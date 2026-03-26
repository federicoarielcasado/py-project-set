"""CLI de CADNorm — interfaz de línea de comandos con Typer.

Comandos:
  generate  Genera un archivo CAD configurado según la norma seleccionada.
  profile   Gestiona perfiles de usuario (listar, exportar, importar).
  info      Muestra parámetros informativos de una norma.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cadnorm.core.db import (
    get_connection,
    init_db,
    delete_profile,
    get_profile,
    list_profiles,
    log_generation,
    save_profile,
)
from cadnorm.core.loader import ProfileLoadError, load_builtin_profile, load_profile
from cadnorm.core.models import NormProfile
from cadnorm.translators.autocad import AutoCADTranslator
from cadnorm.translators.librecad import LibreCADTranslator

# ---------------------------------------------------------------------------
# App y consola
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="cadnorm",
    help="Generador de plantillas CAD configuradas según normas técnicas (IRAM, ISO, ASME).",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

TRANSLATORS = {
    "autocad": AutoCADTranslator,
    "librecad": LibreCADTranslator,
}

# ---------------------------------------------------------------------------
# Sistema de advertencias normativas
# ---------------------------------------------------------------------------

# Códigos de advertencia tipificados
WARN_PARAM_MODIFIED = "WARN-001"   # Parámetro normativo modificado
WARN_OUT_OF_RANGE   = "WARN-002"   # Valor fuera del rango recomendado


def _check_modification_warning(
    field_name: str,
    original_value: object,
    new_value: object,
    norm_ref: Optional[str],
) -> Optional[str]:
    """Devuelve un mensaje de advertencia si corresponde, o None."""
    if str(original_value) == str(new_value):
        return None
    if norm_ref:
        return (
            f"{WARN_PARAM_MODIFIED}: '{field_name}' modificado "
            f"(norm_ref: {norm_ref}). "
            f"Valor normativo: {original_value!r} → nuevo: {new_value!r}"
        )
    return None


# ---------------------------------------------------------------------------
# Wizard interactivo — editor de parámetros
# ---------------------------------------------------------------------------

def _prompt_units(profile_dict: dict, original_profile: NormProfile) -> list[str]:
    """Wizard interactivo para editar la sección 'units'. Devuelve advertencias."""
    warnings: list[str] = []
    u = profile_dict["units"]
    orig = original_profile.units

    console.print("\n[bold cyan]--- Unidades ---[/bold cyan]")
    fields = [
        ("system",              "Sistema (metric/imperial)",   str),
        ("linear_unit",         "Unidad lineal",               str),
        ("linear_precision",    "Precisión lineal (0-8)",      int),
        ("angular_unit",        "Unidad angular",              str),
        ("angular_precision",   "Precisión angular (0-8)",     int),
        ("insertion_scale",     "Escala de inserción",         str),
    ]
    for i, (key, label, cast) in enumerate(fields, 1):
        console.print(f"  [{i}] {label}: [yellow]{u[key]}[/yellow]")

    selection = typer.prompt(
        "Número de parámetro a modificar (Enter para cancelar)",
        default="",
    )
    if not selection.strip():
        return warnings

    try:
        idx = int(selection) - 1
        if not (0 <= idx < len(fields)):
            console.print("[red]Número inválido.[/red]")
            return warnings
    except ValueError:
        console.print("[red]Entrada inválida.[/red]")
        return warnings

    key, label, cast = fields[idx]
    current = u[key]
    new_raw = typer.prompt(f"{label} [{current}]", default=str(current))

    try:
        new_val = cast(new_raw)
    except (ValueError, TypeError):
        console.print(f"[red]Valor inválido para {label}.[/red]")
        return warnings

    norm_ref = None  # units no tienen norm_ref individual en el modelo actual
    warn = _check_modification_warning(key, current, new_val, norm_ref)
    if warn:
        console.print(f"[yellow]⚠ {warn}[/yellow]")
        warnings.append(warn)
    elif str(current) != str(new_val):
        # Siempre advertir cambios en units porque son parámetros base IRAM
        warn_msg = (
            f"{WARN_PARAM_MODIFIED}: '{key}' modificado. "
            f"Valor normativo: {current!r} → nuevo: {new_val!r}"
        )
        console.print(f"[yellow]⚠ {warn_msg}[/yellow]")
        warnings.append(warn_msg)

    u[key] = new_val
    console.print(f"[green]✓ {label} actualizado a {new_val!r}[/green]")
    return warnings


def _prompt_layers(profile_dict: dict, original_profile: NormProfile) -> list[str]:
    """Wizard interactivo para editar capas."""
    warnings: list[str] = []
    layers = profile_dict["layers"]

    console.print("\n[bold cyan]--- Capas ---[/bold cyan]")
    for i, la in enumerate(layers, 1):
        console.print(
            f"  [{i}] {la['name']:<20} color={la['color_aci']:<4} "
            f"linetype={la['linetype']:<15} lw={la['lineweight']}"
        )

    selection = typer.prompt(
        "Número de capa a modificar (Enter para cancelar)",
        default="",
    )
    if not selection.strip():
        return warnings

    try:
        idx = int(selection) - 1
        if not (0 <= idx < len(layers)):
            console.print("[red]Número inválido.[/red]")
            return warnings
    except ValueError:
        console.print("[red]Entrada inválida.[/red]")
        return warnings

    la = layers[idx]
    orig_la = original_profile.layers[idx]
    console.print(f"\n  Editando capa: [bold]{la['name']}[/bold]")

    fields = [
        ("color_aci",    "Color ACI",       int),
        ("linetype",     "Tipo de línea",   str),
        ("lineweight",   "Espesor (1/100mm)", int),
        ("description",  "Descripción",     str),
    ]
    for i, (k, lbl, _) in enumerate(fields, 1):
        console.print(f"    [{i}] {lbl}: [yellow]{la[k]}[/yellow]")

    sel2 = typer.prompt("Número de parámetro (Enter para cancelar)", default="")
    if not sel2.strip():
        return warnings

    try:
        idx2 = int(sel2) - 1
        if not (0 <= idx2 < len(fields)):
            console.print("[red]Número inválido.[/red]")
            return warnings
    except ValueError:
        console.print("[red]Entrada inválida.[/red]")
        return warnings

    key, label, cast = fields[idx2]
    current = la[key]
    new_raw = typer.prompt(f"{label} [{current}]", default=str(current))

    try:
        new_val = cast(new_raw)
    except (ValueError, TypeError):
        console.print(f"[red]Valor inválido para {label}.[/red]")
        return warnings

    norm_ref = orig_la.norm_ref
    field_id = f"layers[{la['name']}].{key}"
    warn = _check_modification_warning(field_id, current, new_val, norm_ref)
    if warn:
        console.print(f"[yellow]⚠ {warn}[/yellow]")
        warnings.append(warn)
    elif str(current) != str(new_val):
        warn_msg = (
            f"{WARN_PARAM_MODIFIED}: '{field_id}' modificado. "
            f"Valor normativo: {current!r} → nuevo: {new_val!r}"
        )
        console.print(f"[yellow]⚠ {warn_msg}[/yellow]")
        warnings.append(warn_msg)

    la[key] = new_val
    console.print(f"[green]✓ {label} actualizado a {new_val!r}[/green]")
    return warnings


def _interactive_wizard(profile: NormProfile) -> tuple[dict, list[str]]:
    """Wizard interactivo completo. Devuelve (profile_dict_modificado, warnings)."""
    profile_dict = json.loads(profile.model_dump_json())
    all_warnings: list[str] = []

    CATEGORIES = {
        "1": ("Unidades",           _prompt_units),
        "2": ("Capas",              _prompt_layers),
    }

    console.print("\n[bold]Parámetros disponibles para editar:[/bold]")
    for k, (name, _) in CATEGORIES.items():
        console.print(f"  [{k}] {name}")
    console.print("  [0] Continuar con valores actuales")

    while True:
        sel = typer.prompt("\nSeleccione categoría", default="0")
        if sel == "0":
            break
        if sel in CATEGORIES:
            _, fn = CATEGORIES[sel]
            warns = fn(profile_dict, profile)
            all_warnings.extend(warns)
        else:
            console.print("[red]Opción no válida.[/red]")

    return profile_dict, all_warnings


# ---------------------------------------------------------------------------
# Comando: generate
# ---------------------------------------------------------------------------

@app.command()
def generate(
    norm: str = typer.Option(..., "--norm", "-n", help="Norma base (ej: iram_general)"),
    software: str = typer.Option(..., "--software", "-s", help="Software CAD destino (autocad, librecad)"),
    output: str = typer.Option("", "--output", "-o", help="Ruta del archivo generado"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Modo wizard interactivo"),
    profile_name: str = typer.Option("", "--profile", "-p", help="Nombre del perfil guardado a usar"),
) -> None:
    """Genera un archivo CAD configurado según la norma seleccionada."""
    software = software.lower()
    if software not in TRANSLATORS:
        console.print(
            f"[red]Software '{software}' no soportado. "
            f"Opciones: {', '.join(TRANSLATORS)}[/red]"
        )
        raise typer.Exit(1)

    # --- Cargar perfil ---
    base_profile: NormProfile
    if profile_name:
        conn = get_connection()
        init_db(conn)
        row = get_profile(conn, profile_name)
        if row is None:
            console.print(f"[red]Perfil '{profile_name}' no encontrado en la base de datos.[/red]")
            raise typer.Exit(1)
        try:
            base_profile = NormProfile.model_validate(row["data"])
        except Exception as e:
            console.print(f"[red]Error al parsear perfil '{profile_name}': {e}[/red]")
            raise typer.Exit(1)
    else:
        try:
            base_profile = load_builtin_profile(norm)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        except ProfileLoadError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    translator_cls = TRANSLATORS[software]
    translator = translator_cls()
    ext = translator.output_extension

    # --- Ruta de salida ---
    if not output:
        output = f"{norm}_{software}{ext}"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Banner ---
    console.print(
        f"\n[bold blue]CADNorm[/bold blue] — "
        f"[cyan]{base_profile.metadata.standard_name}[/cyan] "
        f"v{base_profile.metadata.profile_version} → "
        f"[magenta]{software.upper()}[/magenta] ({ext})"
    )
    console.print(
        f"  Capas: {len(base_profile.layers)} · "
        f"Textos: {len(base_profile.text_styles)} · "
        f"Cotas: {len(base_profile.dim_styles)} · "
        f"Papeles: {len(base_profile.paper_sizes)}"
    )

    # --- Modo interactivo ---
    warnings: list[str] = []
    final_profile = base_profile

    if interactive:
        profile_dict, warnings = _interactive_wizard(base_profile)
        if warnings:
            console.print(f"\n[yellow]⚠ {len(warnings)} advertencia(s) normativa(s)[/yellow]")
            if not typer.confirm("¿Continuar con el perfil modificado?", default=True):
                console.print("[yellow]Generación cancelada.[/yellow]")
                raise typer.Exit(0)
        try:
            final_profile = NormProfile.model_validate(profile_dict)
        except Exception as e:
            console.print(f"[red]El perfil modificado no es válido: {e}[/red]")
            raise typer.Exit(1)

    # --- Generar archivo ---
    console.print(f"\n  Generando → [bold]{output_path}[/bold] ...")
    result = translator.generate(final_profile, output_path)

    # --- Resultado ---
    if result.success:
        console.print(f"[bold green]✓ Archivo generado:[/bold green] {result.output_path}")
        if result.stats:
            for k, v in result.stats.items():
                console.print(f"    {k}: {v}")
    else:
        console.print("[bold red]✗ La generación falló.[/bold red]")
        for e in result.errors:
            console.print(f"  [red]ERROR: {e}[/red]")

    all_warnings = warnings + result.warnings
    for w in all_warnings:
        console.print(f"  [yellow]⚠ {w}[/yellow]")

    # --- Log en SQLite ---
    try:
        conn = get_connection()
        init_db(conn)
        log_generation(
            conn,
            profile_name=norm,
            software=software,
            output_path=str(output_path),
            success=result.success,
            warnings=all_warnings,
        )
    except Exception:
        pass  # El log es best-effort; no interrumpe el flujo

    if not result.success:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Comando: profile
# ---------------------------------------------------------------------------

@app.command()
def profile(
    action: str = typer.Argument(..., help="Acción: list | export | import | delete"),
    name: str = typer.Option("", "--name", "-n", help="Nombre del perfil"),
    output: str = typer.Option("", "--output", "-o", help="Archivo destino (export)"),
    input_file: str = typer.Option("", "--input", "-f", help="Archivo origen (import)"),
    norm: str = typer.Option("", "--norm", help="Norma base actual para guardar junto al perfil importado"),
) -> None:
    """Gestiona perfiles de usuario (listar, exportar, importar, eliminar)."""
    conn = get_connection()
    init_db(conn)

    action = action.lower()

    if action == "list":
        rows = list_profiles(conn)
        if not rows:
            console.print("[dim]No hay perfiles guardados.[/dim]")
            return
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("ID", justify="right", style="dim")
        table.add_column("Nombre")
        table.add_column("Norma base")
        table.add_column("Creado", style="dim")
        table.add_column("Actualizado", style="dim")
        for r in rows:
            table.add_row(
                str(r["id"]),
                r["name"],
                r["standard_name"],
                r["created_at"][:10],
                r["updated_at"][:10],
            )
        console.print(table)

    elif action == "export":
        if not name:
            console.print("[red]--name requerido para export.[/red]")
            raise typer.Exit(1)
        row = get_profile(conn, name)
        if row is None:
            console.print(f"[red]Perfil '{name}' no encontrado.[/red]")
            raise typer.Exit(1)
        dest = Path(output) if output else Path(f"{name}.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(row["data"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"[green]✓ Perfil '{name}' exportado → {dest}[/green]")

    elif action == "import":
        if not input_file:
            console.print("[red]--input requerido para import.[/red]")
            raise typer.Exit(1)
        src = Path(input_file)
        if not src.exists():
            console.print(f"[red]Archivo no encontrado: {src}[/red]")
            raise typer.Exit(1)
        try:
            loaded = load_profile(src)
        except ProfileLoadError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error al leer el archivo: {e}[/red]")
            raise typer.Exit(1)

        profile_name = name or src.stem
        standard = norm or loaded.metadata.standard_name
        data_dict = json.loads(loaded.model_dump_json(exclude_none=True))
        pid = save_profile(conn, profile_name, standard, data_dict)
        console.print(
            f"[green]✓ Perfil '{profile_name}' importado (id={pid}, norma={standard})[/green]"
        )

    elif action == "delete":
        if not name:
            console.print("[red]--name requerido para delete.[/red]")
            raise typer.Exit(1)
        if not typer.confirm(f"¿Eliminar perfil '{name}'?", default=False):
            console.print("[yellow]Cancelado.[/yellow]")
            raise typer.Exit(0)
        from cadnorm.core.db import delete_profile as _del
        if _del(conn, name):
            console.print(f"[green]✓ Perfil '{name}' eliminado.[/green]")
        else:
            console.print(f"[red]Perfil '{name}' no encontrado.[/red]")
            raise typer.Exit(1)

    else:
        console.print(f"[red]Acción '{action}' no reconocida. Opciones: list, export, import, delete[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Comando: info
# ---------------------------------------------------------------------------

_INFO_CATEGORIES = {
    "units":          ("Unidades",              lambda p: [p.units]),
    "layers":         ("Capas",                 lambda p: p.layers),
    "linetypes":      ("Tipos de línea",        lambda p: p.linetypes),
    "text_styles":    ("Estilos de texto",      lambda p: p.text_styles),
    "dim_styles":     ("Estilos de cotas",      lambda p: p.dim_styles),
    "drawing_scales": ("Escalas de dibujo",     lambda p: p.drawing_scales),
    "paper_sizes":    ("Tamaños de papel",      lambda p: p.paper_sizes),
    "hatch_patterns": ("Patrones de hachurado", lambda p: p.hatch_patterns),
    "plot_config":    ("Configuración de impresión", lambda p: [p.plot_config]),
    "title_block":    ("Rótulo",                lambda p: [p.title_block]),
    "metadata":       ("Metadatos",             lambda p: [p.metadata]),
}


@app.command()
def info(
    norm: str = typer.Option(..., "--norm", "-n", help="Norma a consultar (ej: iram_general)"),
    category: str = typer.Option("", "--category", "-c", help="Categoría: " + ", ".join(_INFO_CATEGORIES)),
) -> None:
    """Muestra parámetros de una norma (referencia informativa)."""
    try:
        loaded = load_builtin_profile(norm)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except ProfileLoadError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(
        f"\n[bold blue]{loaded.metadata.standard_name}[/bold blue] "
        f"v{loaded.metadata.profile_version} — {loaded.metadata.description}"
    )
    console.print(f"  Fuente: {loaded.metadata.source}")
    console.print(f"  Vigencia: {loaded.metadata.effective_date}")

    cats_to_show = [category.lower()] if category else list(_INFO_CATEGORIES.keys())

    for cat in cats_to_show:
        if cat not in _INFO_CATEGORIES:
            console.print(f"[red]Categoría '{cat}' no reconocida. Opciones: {', '.join(_INFO_CATEGORIES)}[/red]")
            raise typer.Exit(1)

        label, getter = _INFO_CATEGORIES[cat]
        items = getter(loaded)

        console.print(f"\n[bold cyan]-- {label} --[/bold cyan]")
        for item in items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else {}
            for k, v in item_dict.items():
                if isinstance(v, list):
                    console.print(f"  [bold]{k}[/bold]: ({len(v)} elementos)")
                    for elem in v:
                        if hasattr(elem, "model_dump"):
                            elem_d = elem.model_dump()
                            name_key = next(
                                (x for x in ("name", "label", "id") if x in elem_d), None
                            )
                            if name_key:
                                console.print(f"    • {elem_d[name_key]}")
                        else:
                            console.print(f"    • {elem}")
                else:
                    norm_ref_str = ""
                    if k != "norm_ref" and hasattr(item, "norm_ref") and item.norm_ref:
                        norm_ref_str = f" [dim](ref: {item.norm_ref})[/dim]"
                    if k == "norm_ref":
                        continue
                    console.print(f"  [bold]{k}[/bold]: {v}{norm_ref_str}")


if __name__ == "__main__":
    app()
