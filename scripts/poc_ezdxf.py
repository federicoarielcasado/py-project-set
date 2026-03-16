"""POC ezdxf — Sprint 0.

Valida que ezdxf puede crear:
- Capas con color ACI, tipo de línea y espesor (lineweight)
- Tipos de línea personalizados
- Estilos de texto con fuente SHX
- Geometría básica en cada capa

Genera: output/minimal_iram.dxf

Uso:
    python scripts/poc_ezdxf.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite ejecutar desde la raíz del proyecto sin instalar el paquete
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
except ImportError:
    print("ERROR: ezdxf no está instalado. Ejecutá: pip install ezdxf")
    sys.exit(1)


PROFILE_PATH = Path(__file__).parent.parent / "cadnorm" / "standards" / "iram_general.json"
OUTPUT_PATH = Path(__file__).parent.parent / "output" / "minimal_iram.dxf"


def load_profile() -> dict:
    with PROFILE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def create_document() -> ezdxf.document.Drawing:
    doc = ezdxf.new(dxfversion="R2010", setup=True)
    doc.header["$MEASUREMENT"] = 1   # métrico
    doc.header["$INSUNITS"] = 4      # milímetros
    doc.header["$LUNITS"] = 2        # decimal
    doc.header["$LUPREC"] = 2        # 2 decimales
    doc.header["$AUNITS"] = 0        # grados
    doc.header["$AUPREC"] = 0        # 0 decimales angulares
    return doc


def add_linetypes(doc: ezdxf.document.Drawing, linetypes: list[dict]) -> dict[str, str]:
    """Carga tipos de línea en el documento. Retorna mapa nombre→estado."""
    results = {}
    ltype_table = doc.linetypes
    for lt in linetypes:
        name = lt["name"]
        if name == "CONTINUOUS":
            results[name] = "built-in"
            continue
        try:
            if not ltype_table.has_entry(name):
                pattern = lt.get("pattern", "")
                if pattern:
                    ltype_table.add(name, pattern=pattern, description=lt.get("description", ""))
                else:
                    ltype_table.add(name, pattern="A", description=lt.get("description", ""))
            results[name] = "OK"
        except Exception as e:
            results[name] = f"WARN: {e}"
    return results


def add_layers(doc: ezdxf.document.Drawing, layers: list[dict]) -> dict[str, str]:
    """Crea capas con color ACI, tipo de línea y espesor."""
    results = {}
    layer_table = doc.layers
    for layer in layers:
        name = layer["name"]
        try:
            if layer_table.has_entry(name):
                lyr = layer_table.get(name)
            else:
                lyr = layer_table.add(name)
            lyr.color = layer["color_aci"]
            lyr.linetype = layer["linetype"]
            lyr.lineweight = layer["lineweight"]
            lyr.plot = layer.get("plot", True)
            results[name] = "OK"
        except Exception as e:
            results[name] = f"WARN: {e}"
    return results


def add_text_styles(doc: ezdxf.document.Drawing, text_styles: list[dict]) -> dict[str, str]:
    """Crea estilos de texto."""
    results = {}
    style_table = doc.styles
    for ts in text_styles:
        name = ts["name"]
        try:
            if style_table.has_entry(name):
                style = style_table.get(name)
            else:
                style = style_table.add(name, font=ts["font"])
            style.dxf.height = ts["height"]
            style.dxf.width = ts.get("width_factor", 1.0)
            style.dxf.oblique = ts.get("oblique_angle", 0.0)
            results[name] = "OK"
        except Exception as e:
            results[name] = f"WARN: {e}"
    return results


def draw_sample_geometry(doc: ezdxf.document.Drawing, layers: list[dict]) -> None:
    """Dibuja geometría mínima en cada capa para visualización."""
    msp = doc.modelspace()
    y = 0.0
    for layer in layers:
        name = layer["name"]
        # Línea horizontal de muestra
        msp.add_line(
            start=(0, y),
            end=(100, y),
            dxfattribs={"layer": name},
        )
        # Texto etiqueta
        msp.add_text(
            name,
            dxfattribs={"layer": name, "height": 3.5, "insert": (105, y - 1.5)},
        )
        y -= 15.0


def main() -> None:
    print("=" * 60)
    print("CADNorm — POC ezdxf")
    print(f"ezdxf version: {ezdxf.__version__}")
    print("=" * 60)

    # 1. Cargar perfil IRAM
    print("\n[1] Cargando perfil IRAM...")
    profile = load_profile()
    meta = profile["metadata"]
    print(f"    Norma: {meta['standard_name']} v{meta['standard_version']}")

    # 2. Crear documento DXF
    print("\n[2] Creando documento DXF R2010...")
    doc = create_document()
    print("    OK")

    # 3. Tipos de línea
    print("\n[3] Cargando tipos de línea...")
    lt_results = add_linetypes(doc, profile["linetypes"])
    for name, status in lt_results.items():
        print(f"    {name}: {status}")

    # 4. Capas
    print("\n[4] Creando capas...")
    layer_results = add_layers(doc, profile["layers"])
    for name, status in layer_results.items():
        print(f"    {name}: {status}")

    # 5. Estilos de texto
    print("\n[5] Creando estilos de texto...")
    text_results = add_text_styles(doc, profile["text_styles"])
    for name, status in text_results.items():
        print(f"    {name}: {status}")

    # 6. Geometría de muestra
    print("\n[6] Dibujando geometría de muestra...")
    draw_sample_geometry(doc, profile["layers"])
    print("    OK")

    # 7. Guardar
    print(f"\n[7] Guardando en: {OUTPUT_PATH}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(OUTPUT_PATH))
    print("    OK")

    # 8. Resumen
    ok_layers = sum(1 for s in layer_results.values() if s == "OK")
    ok_lt = sum(1 for s in lt_results.values() if "WARN" not in s)
    ok_ts = sum(1 for s in text_results.values() if s == "OK")

    print("\n" + "=" * 60)
    print("RESUMEN POC")
    print(f"  Capas creadas:          {ok_layers}/{len(layer_results)}")
    print(f"  Tipos de línea:         {ok_lt}/{len(lt_results)}")
    print(f"  Estilos de texto:       {ok_ts}/{len(text_results)}")
    print(f"  Archivo generado:       {OUTPUT_PATH.name}")
    print(f"  Tamaño:                 {OUTPUT_PATH.stat().st_size:,} bytes")

    warns = [s for s in {**layer_results, **lt_results, **text_results}.values() if "WARN" in str(s)]
    if warns:
        print(f"\n  Advertencias ({len(warns)}):")
        for w in warns:
            print(f"    - {w}")
        print("\n  -> Documentar limitaciones de ezdxf para Sprint 2")
    else:
        print("\n  Sin advertencias — ezdxf soporta todos los parámetros IRAM")
    print("=" * 60)


if __name__ == "__main__":
    main()
