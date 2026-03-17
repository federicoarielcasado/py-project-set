"""Traductor AutoCAD — genera archivos .dwt vía ezdxf.

Implementa la conversión completa de un NormProfile a un archivo plantilla
AutoCAD (.dwt), aplicando:
  - Variables de encabezado (unidades, escala)
  - Tipos de línea (IRAM 4502)
  - Capas con color ACI, tipo de línea y espesor (IRAM 4502)
  - Estilos de texto con fuente SHX (IRAM 4503)
  - Estilos de cota (IRAM 4513)

Patrón Strategy: implementa la interfaz Translator definida en base.py.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import ezdxf

from cadnorm.core.models import NormProfile
from cadnorm.translators.base import GenerationResult, Translator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de mapeo
# ---------------------------------------------------------------------------

# INSUNITS AutoCAD/DXF → código numérico
_INSUNITS: dict[str, int] = {
    "mm": 4,
    "cm": 5,
    "m": 6,
    "in": 1,
    "ft": 2,
    "unitless": 0,
}

# Nombres descriptivos de flechas → nombres internos ezdxf (vacío = closed filled)
_ARROW_MAP: dict[str, str] = {
    "": "",
    "CLOSED_FILLED": "",
    "DOT": "DOT",
    "DOTSMALL": "DOTSMALL",
    "OPEN": "OPEN",
    "OPEN90": "OPEN90",
    "OPEN30": "OPEN30",
    "OBLIQUE": "OBLIQUE",
    "_NONE": "_NONE",
    "DOTBLANK": "DOTBLANK",
    "CLOSEDBLANK": "_CLOSEDBLANK",
}


# ---------------------------------------------------------------------------
# Traductor AutoCAD
# ---------------------------------------------------------------------------

class AutoCADTranslator(Translator):
    """Traduce un perfil normativo a un archivo plantilla AutoCAD (.dwt)."""

    @property
    def software_name(self) -> str:
        return "autocad"

    @property
    def output_extension(self) -> str:
        return ".dwt"

    def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult:
        """Genera un archivo .dwt con la configuración completa del perfil normativo.

        Args:
            profile: Perfil normativo validado por Pydantic.
            output_path: Ruta destino del archivo .dwt.

        Returns:
            GenerationResult con éxito/fallo, warnings y estadísticas.
        """
        warnings: list[str] = []

        try:
            # 1. Crear documento DXF R2010 con tipos de línea estándar precargados
            doc = ezdxf.new(dxfversion="R2010", setup=True)

            # 2. Variables de encabezado (unidades IRAM — métrico, mm)
            _apply_header(doc, profile)

            # 3. Tipos de línea (IRAM 4502)
            lt_count = _apply_linetypes(doc, profile.linetypes, warnings)

            # 4. Capas (IRAM 4502)
            la_count = _apply_layers(doc, profile.layers, warnings)

            # 5. Estilos de texto (IRAM 4503)
            ts_count = _apply_text_styles(doc, profile.text_styles, warnings)

            # 6. Estilos de cota (IRAM 4513)
            ds_count = _apply_dim_styles(doc, profile.dim_styles, warnings)

            # 7. Guardar (crea directorio si no existe)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(output_path))

            return GenerationResult(
                success=True,
                output_path=output_path,
                warnings=warnings,
                stats={
                    "linetypes": lt_count,
                    "layers": la_count,
                    "text_styles": ts_count,
                    "dim_styles": ds_count,
                },
            )

        except Exception as exc:
            logger.exception("Error generando archivo AutoCAD")
            return GenerationResult(
                success=False,
                errors=[f"Error de generación: {exc}"],
            )


# ---------------------------------------------------------------------------
# Funciones internas de aplicación — reutilizables por LibreCADTranslator
# ---------------------------------------------------------------------------

def _apply_header(doc: ezdxf.document.Drawing, profile: NormProfile) -> None:
    """Configura variables de encabezado DXF según el perfil normativo."""
    u = profile.units
    doc.header["$INSUNITS"] = _INSUNITS.get(u.linear_unit, 4)
    doc.header["$MEASUREMENT"] = u.measurement_system   # 1 = métrico
    doc.header["$LUNITS"] = 2                            # 2 = decimal
    doc.header["$LUPREC"] = u.linear_precision
    doc.header["$AUNITS"] = 0                            # 0 = grados
    doc.header["$AUPREC"] = u.angular_precision
    doc.header["$LTSCALE"] = 1.0                         # escala global tipos de línea
    doc.header["$DIMSCALE"] = 1.0                        # escala global de cotas


def _apply_linetypes(
    doc: ezdxf.document.Drawing,
    linetypes: list,
    warnings: list[str],
) -> int:
    """Registra tipos de línea en el documento.

    Los tipos CONTINUOUS, BYLAYER y BYBLOCK son built-in y se omiten.
    Si el tipo ya existe (cargado por setup=True), se respeta el existente.

    Returns:
        Cantidad de tipos de línea nuevos registrados.
    """
    count = 0
    for lt in linetypes:
        name = lt.name
        if name.upper() in ("CONTINUOUS", "BYLAYER", "BYBLOCK"):
            continue
        if doc.linetypes.has_entry(name):
            continue
        try:
            pattern = lt.pattern.strip() if lt.pattern else ""
            if pattern:
                doc.linetypes.add(name, pattern=pattern, description=lt.description)
            else:
                doc.linetypes.add(name, pattern="A", description=lt.description)
            count += 1
        except Exception as exc:
            warnings.append(f"WARN-002: Tipo de línea '{name}' no creado: {exc}")
    return count


def _apply_layers(
    doc: ezdxf.document.Drawing,
    layers: list,
    warnings: list[str],
) -> int:
    """Crea o actualiza capas con color ACI, tipo de línea y espesor.

    Returns:
        Cantidad de capas creadas o actualizadas.
    """
    count = 0
    for la in layers:
        try:
            if doc.layers.has_entry(la.name):
                layer = doc.layers.get(la.name)
            else:
                layer = doc.layers.add(la.name)

            layer.color = la.color_aci
            layer.linetype = la.linetype
            layer.lineweight = la.lineweight
            layer.dxf.plot = int(la.plot)   # 1=imprimir, 0=no imprimir (DXF grupo 290)

            if la.locked:
                layer.lock()
            if la.frozen:
                layer.freeze()

            count += 1
        except Exception as exc:
            warnings.append(f"WARN-003: Capa '{la.name}' no creada/actualizada: {exc}")
    return count


def _apply_text_styles(
    doc: ezdxf.document.Drawing,
    text_styles: list,
    warnings: list[str],
) -> int:
    """Crea o actualiza estilos de texto con fuente SHX y propiedades IRAM 4503.

    Returns:
        Cantidad de estilos creados o actualizados.
    """
    count = 0
    for ts in text_styles:
        try:
            if doc.styles.has_entry(ts.name):
                style = doc.styles.get(ts.name)
            else:
                style = doc.styles.add(ts.name, font=ts.font)

            style.dxf.height = ts.height
            style.dxf.width = ts.width_factor
            style.dxf.oblique = ts.oblique_angle
            count += 1
        except Exception as exc:
            warnings.append(f"WARN-004: Estilo de texto '{ts.name}' no creado: {exc}")
    return count


def _apply_dim_styles(
    doc: ezdxf.document.Drawing,
    dim_styles: list,
    warnings: list[str],
) -> int:
    """Crea o actualiza estilos de cota según IRAM 4513.

    Returns:
        Cantidad de estilos de cota creados o actualizados.
    """
    count = 0
    for ds in dim_styles:
        try:
            if doc.dimstyles.has_entry(ds.name):
                dimstyle = doc.dimstyles.get(ds.name)
            else:
                dimstyle = doc.dimstyles.new(ds.name)

            # Parámetros dimensionales
            dimstyle.dxf.dimscale = ds.dimscale
            dimstyle.dxf.dimtxt = ds.dimtxt
            dimstyle.dxf.dimexo = ds.dimexo
            dimstyle.dxf.dimexe = ds.dimexe
            dimstyle.dxf.dimasz = ds.dimasz
            dimstyle.dxf.dimgap = ds.dimgap

            # Formato numérico
            dimstyle.dxf.dimdec = ds.dimdec
            dimstyle.dxf.dimadec = ds.dimadec
            dimstyle.dxf.dimlunit = ds.dimlunit

            # Orientación del texto
            dimstyle.dxf.dimtih = int(ds.dimtih)
            dimstyle.dxf.dimtoh = int(ds.dimtoh)

            # Colores ACI
            dimstyle.dxf.dimclrd = ds.dimclrd
            dimstyle.dxf.dimclre = ds.dimclre
            dimstyle.dxf.dimclrt = ds.dimclrt

            # Estilo de texto para cotas (nombre — ezdxf convierte a handle al exportar)
            if ds.dimtxsty and doc.styles.has_entry(ds.dimtxsty):
                dimstyle.dxf.dimtxsty = ds.dimtxsty
            elif ds.dimtxsty:
                warnings.append(
                    f"WARN-005: Estilo de texto '{ds.dimtxsty}' para cota "
                    f"'{ds.name}' no encontrado — se usa estilo por defecto"
                )

            # Tipo de flecha (vacío = closed filled, default IRAM 4513)
            arrow_key = ds.dimblk.upper() if ds.dimblk else ""
            arrow_val = _ARROW_MAP.get(arrow_key, "")
            if arrow_val != "":
                # Solo setear si no es el default (evita errores en versiones viejas)
                try:
                    dimstyle.set_arrows(arrow_val)
                except AttributeError:
                    pass  # API no disponible en esta versión de ezdxf

            count += 1

        except Exception as exc:
            warnings.append(f"WARN-006: Estilo de cota '{ds.name}' no creado: {exc}")

    return count
