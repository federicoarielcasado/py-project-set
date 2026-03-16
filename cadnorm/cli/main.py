"""CLI de CADNorm — interfaz de línea de comandos con Typer.

Sprint 3 implementa el wizard completo con editor de parámetros.
Sprint 0: esqueleto con comandos definidos.
"""
# TODO Sprint 3: implementar lógica completa de cada comando

import typer

app = typer.Typer(
    name="cadnorm",
    help="Generador de plantillas CAD configuradas según normas técnicas (IRAM, ISO, ASME).",
    add_completion=False,
)


@app.command()
def generate(
    norm: str = typer.Option(..., "--norm", "-n", help="Norma base (ej: iram_general)"),
    software: str = typer.Option(..., "--software", "-s", help="Software CAD destino (autocad, librecad)"),
    output: str = typer.Option("output.dxf", "--output", "-o", help="Ruta del archivo generado"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Modo wizard interactivo"),
) -> None:
    """Genera un archivo CAD configurado según la norma seleccionada."""
    # TODO Sprint 2/3: integrar con Translator y loader
    typer.echo(f"[cadnorm] Generando plantilla {norm!r} para {software!r} → {output!r}")
    typer.echo("  (implementación completa en Sprint 2)")


@app.command()
def profile(
    action: str = typer.Argument(..., help="Acción: export | import | list"),
    name: str = typer.Option("", "--name", help="Nombre del perfil"),
    output: str = typer.Option("", "--output", "-o", help="Archivo destino para export"),
    input_file: str = typer.Option("", "--input", help="Archivo origen para import"),
) -> None:
    """Gestiona perfiles de usuario (exportar, importar, listar)."""
    # TODO Sprint 3: implementar export/import JSON y listado desde SQLite
    typer.echo(f"[cadnorm] profile {action!r} — implementación completa en Sprint 3")


@app.command()
def info(
    norm: str = typer.Option(..., "--norm", "-n", help="Norma a consultar"),
    category: str = typer.Option("", "--category", "-c", help="Categoría (layers, scales, etc.)"),
) -> None:
    """Muestra parámetros informativos de una norma."""
    # TODO Sprint 3: mostrar parámetros normativos desde el perfil JSON
    typer.echo(f"[cadnorm] info {norm!r} / {category or 'all'!r} — implementación completa en Sprint 3")


if __name__ == "__main__":
    app()
