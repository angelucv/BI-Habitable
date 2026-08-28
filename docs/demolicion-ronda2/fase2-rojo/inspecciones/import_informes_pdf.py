"""Importación de informes PDF (formato libre) desde carpeta + cruce CSV."""
from __future__ import annotations

import csv
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.files import File
from django.db import transaction

from inspecciones import choices as ch
from inspecciones.models import CasoRojo, InformePdfAdjunto


def _norm(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = t.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _txt(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none") else s


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _fecha(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    m = re.match(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", s.lower())
    if m:
        dia, mes_txt, anio = m.groups()
        mes = meses.get(mes_txt[:3] if len(mes_txt) > 4 else mes_txt)
        if not mes and mes_txt.startswith("sep"):
            mes = 9
        if mes:
            return date(int(anio), mes, int(dia))
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            continue
    return None


def _map_repar_viable(raw: str) -> str:
    r = raw.lower()
    if "detect" in r or not r:
        return ch.SiNoInsuf.PENDIENTE
    if "insuf" in r:
        return ch.SiNoInsuf.INSUF
    # Columna inviabilidad_reparacion: «Sí» = reparación no viable
    if r.startswith("s") or "inviab" in r:
        return ch.SiNoInsuf.NO
    if r.startswith("n"):
        return ch.SiNoInsuf.SI
    return ch.SiNoInsuf.PENDIENTE


def _map_sistema(raw: str) -> str:
    r = raw.lower()
    if "portico" in r or "pórtico" in r or "portic" in r:
        return ch.SistemaEstructural.PORTICOS
    if "muro" in r and "concreto" in r:
        return ch.SistemaEstructural.MUROS
    if "mixto" in r:
        return ch.SistemaEstructural.MIXTO
    if "acero" in r:
        return ch.SistemaEstructural.ACERO
    if "mamposter" in r:
        return ch.SistemaEstructural.MAMPOSTERIA
    return ch.SistemaEstructural.OTRO if raw else ch.SistemaEstructural.PENDIENTE


def _map_decision_d(row: dict[str, Any]) -> str | None:
    dictamen = _txt(row.get("dictamen_etiqueta")).lower()
    recom = _txt(row.get("recomienda_demolicion")).lower()
    inviab = _txt(row.get("inviabilidad_reparacion")).lower()
    tipo = _txt(row.get("tipo_informe")).lower()

    if any(k in dictamen for k in ("colapso", "escombros")) or "post-colapso" in tipo or "escombros" in tipo:
        return ch.DecisionD.D4
    if recom.startswith("s") or "demol" in dictamen:
        return ch.DecisionD.D3
    if inviab.startswith("s") and "detect" not in inviab:
        return ch.DecisionD.D3
    if "insuf" in inviab or "no detect" in inviab:
        return ch.DecisionD.D1
    return None


def _flags_a_texto(flags_raw: str) -> tuple[str, dict[str, str]]:
    flags = [f.strip() for f in _txt(flags_raw).split(";") if f.strip()]
    medidas_partes: list[str] = []
    campos: dict[str, str] = {}

    if "peligro_aledanos" in flags:
        campos["peligro_aledanos"] = ch.PeligroAledanos.SI
        medidas_partes.append("Evaluar y proteger edificaciones aledañas")
    if "acordonamiento" in flags:
        medidas_partes.append("Acordonamiento perimetral")
    if "dano_vigas" in flags:
        campos["dano_vigas"] = ch.NivelABC.B
    if "dano_losas" in flags:
        campos["vig_nivel"] = ch.NivelABC.B
    if "falla_columnas" in flags:
        campos["col_nivel"] = ch.NivelABC.C
    if "perdida_verticalidad" in flags:
        campos["inclinacion"] = ch.Inclinacion.SI_CUAL
    if "cerramientos" in flags:
        campos["riesgo_fachada"] = ch.NivelABC.B

    return "; ".join(medidas_partes), campos


def _justificacion_desde_cruce(row: dict[str, Any]) -> str:
    partes: list[str] = []
    tipo = _txt(row.get("tipo_informe"))
    codigo = _txt(row.get("codigo_documento"))
    dictamen = _txt(row.get("dictamen_etiqueta"))
    if tipo:
        partes.append(f"Tipo: {tipo}")
    if codigo:
        partes.append(f"Código documento: {codigo}")
    if dictamen:
        partes.append(f"Dictamen informe: {dictamen}")
    match = _txt(row.get("match_calidad"))
    if match:
        partes.append(f"Cruce Habitable: {match}")
    return ". ".join(partes) + ("." if partes else "")


def cargar_indice_cruce(csv_path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Índice por nombre de archivo y por nombre normalizado."""
    by_file: dict[str, dict] = {}
    by_norm: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            archivo = _txt(row.get("archivo_pdf"))
            if not archivo:
                continue
            by_file[archivo.lower()] = row
            by_file[Path(archivo).name.lower()] = row
            norm = _txt(row.get("nombre_archivo_norm")) or _norm(Path(archivo).stem)
            if norm:
                by_norm[norm] = row
    return by_file, by_norm


def buscar_fila_cruce(
    pdf_path: Path, by_file: dict[str, dict], by_norm: dict[str, dict]
) -> dict | None:
    name = pdf_path.name
    row = by_file.get(name.lower())
    if row:
        return row
    stem_norm = _norm(pdf_path.stem)
    return by_norm.get(stem_norm)


def enriquecer_caso_desde_cruce(caso: CasoRojo, row: dict[str, Any], *, sobrescribir: bool) -> list[str]:
    """Completa campos visita 2 / decisión desde fila del cruce. Devuelve campos tocados."""
    actualizados: list[str] = []

    def set_if(field: str, value: Any) -> None:
        if value in (None, ""):
            return
        actual = getattr(caso, field)
        if actual and not sobrescribir:
            return
        setattr(caso, field, value)
        actualizados.append(field)

    set_if("nombre_conf", _txt(row.get("nombre_edificacion_informe")))
    set_if("fecha_v2", _fecha(row.get("fecha_inspeccion_informe")))
    set_if("evaluadores_v2", _txt(row.get("evaluadores")))
    set_if("supervisor_v2", _txt(row.get("supervisor")))
    set_if("uso", _txt(row.get("uso")) or _txt(row.get("hab_uso")))
    set_if("piso_crit_v2", _txt(row.get("piso_critico_mencionado")))
    extracto = _txt(row.get("extracto_conclusiones"))
    if extracto:
        set_if("analisis_libre", extracto[:8000])
        set_if("resumen_ejecutivo", extracto[:4000])

    pisos = row.get("num_pisos_informe")
    if pisos not in (None, ""):
        set_if("pisos_conf", _txt(pisos).split(".")[0])
    elif _txt(row.get("hab_num_pisos")):
        set_if("pisos_conf", _txt(row.get("hab_num_pisos")).split(".")[0])
    sot = row.get("num_sotanos_informe")
    if sot not in (None, ""):
        set_if("sotanos_conf", _txt(sot).split(".")[0])

    sistema = _txt(row.get("sistema_estructural")) or _txt(row.get("hab_material"))
    if sistema:
        set_if("sistema", _map_sistema(sistema))

    lat = _decimal(row.get("lat_informe")) or _decimal(row.get("hab_lat"))
    lng = _decimal(row.get("lon_informe")) or _decimal(row.get("hab_lng"))
    if lat is not None and lng is not None:
        set_if("gps_v2", f"{lat}, {lng}")
        set_if("lat", lat)
        set_if("lng", lng)

    inviab = _txt(row.get("inviabilidad_reparacion"))
    if inviab and "detect" not in inviab.lower():
        set_if("repar_viable", _map_repar_viable(inviab))

    decision = _map_decision_d(row)
    if decision:
        set_if("decision_D", decision)
        if decision in (ch.DecisionD.D3, ch.DecisionD.D4):
            set_if("prioridad", ch.PrioridadOperativa.INMEDIATA)
        elif decision == ch.DecisionD.D1:
            set_if("prioridad", ch.PrioridadOperativa.ALTA)

    dictamen = _txt(row.get("dictamen_etiqueta")).lower()
    if "inseguro" in dictamen or "rojo" in dictamen:
        set_if("val_etiqueta", ch.SiNoInsuf.SI)

    medidas_flags, campos_flags = _flags_a_texto(_txt(row.get("hallazgos_flags")))
    obs_hab = _txt(row.get("hab_obs"))
    medidas_txt = medidas_flags
    if obs_hab:
        medidas_txt = f"{medidas_txt}; {obs_hab}" if medidas_txt else obs_hab
    if medidas_txt:
        set_if("medidas", medidas_txt[:2000])

    for campo, valor in campos_flags.items():
        set_if(campo, valor)

    n_fotos = _int(row.get("n_evidencias_fotograficas_citadas"))
    if n_fotos:
        set_if("n_fotos", str(n_fotos))

    just = _justificacion_desde_cruce(row)
    if just:
        set_if("justificacion", just[:4000])

    ubic = _txt(row.get("ubicacion_informe"))
    if ubic and not caso.direccion_hab:
        set_if("direccion_hab", ubic[:500])

    if caso.estado_2da == ch.Estado2daRonda.PENDIENTE:
        set_if("estado_2da", ch.Estado2daRonda.BORRADOR)

    return actualizados


@transaction.atomic
def importar_carpeta_informes(
    carpeta: Path,
    csv_path: Path | None = None,
    *,
    dry_run: bool = False,
    sobrescribir_campos: bool = False,
    reemplazar_pdf: bool = False,
) -> dict[str, int]:
    stats = {
        "pdfs_en_carpeta": 0,
        "vinculados": 0,
        "sin_caso": 0,
        "sin_cruce": 0,
        "omitidos_dup": 0,
        "casos_enriquecidos": 0,
        "errores": 0,
    }

    by_file: dict[str, dict] = {}
    by_norm: dict[str, dict] = {}
    if csv_path and csv_path.is_file():
        by_file, by_norm = cargar_indice_cruce(csv_path)

    pdfs = sorted(carpeta.glob("*.pdf"))
    stats["pdfs_en_carpeta"] = len(pdfs)

    for pdf_path in pdfs:
        try:
            row = buscar_fila_cruce(pdf_path, by_file, by_norm) if by_file else None
            hab_id = _int(row.get("hab_id")) if row else None

            if not hab_id:
                stats["sin_cruce" if row is None else "sin_caso"] += 1
                continue

            caso = CasoRojo.objects.filter(hab_id=hab_id).first()
            if not caso:
                stats["sin_caso"] += 1
                continue

            if dry_run:
                stats["vinculados"] += 1
                continue

            exists = InformePdfAdjunto.objects.filter(
                caso=caso, nombre_archivo_origen=pdf_path.name
            ).exists()
            if exists and not reemplazar_pdf:
                stats["omitidos_dup"] += 1
                continue

            if exists and reemplazar_pdf:
                InformePdfAdjunto.objects.filter(
                    caso=caso, nombre_archivo_origen=pdf_path.name
                ).delete()

            titulo = _txt(row.get("nombre_edificacion_informe")) if row else pdf_path.stem
            tipo_inf = _txt(row.get("tipo_informe")) if row else "Informe PDF (formato libre)"

            with pdf_path.open("rb") as fh:
                doc = InformePdfAdjunto(
                    caso=caso,
                    titulo=titulo or pdf_path.stem,
                    nombre_archivo_origen=pdf_path.name,
                    tipo_informe=tipo_inf,
                    codigo_documento=_txt(row.get("codigo_documento")) if row else "",
                    notas=f"Carga inicial desde {pdf_path.name}",
                )
                doc.archivo.save(pdf_path.name, File(fh), save=True)

            stats["vinculados"] += 1

            if row:
                campos = enriquecer_caso_desde_cruce(caso, row, sobrescribir=sobrescribir_campos)
                if campos:
                    caso.save(update_fields=campos + ["updated_at"])
                    stats["casos_enriquecidos"] += 1

        except Exception:
            stats["errores"] += 1

    return stats
