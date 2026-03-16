# CADNorm 📐

**Generador de plantillas CAD configuradas según normas técnicas de dibujo (IRAM, ISO, ASME)**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-9%20passing-brightgreen)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Estado-Sprint%200%20%E2%80%94%20Setup-orange)]()

---

## 📋 Descripción

CADNorm automatiza la configuración inicial de archivos CAD según normas técnicas de dibujo. En lugar de configurar manualmente capas, estilos de texto, cotas y unidades para cada proyecto nuevo, CADNorm genera plantillas `.dwt` (AutoCAD) y `.dxf` (LibreCAD) completamente configuradas desde la línea de comandos.

| Componente | Descripción |
|------------|-------------|
| `cadnorm/standards/` | Perfiles normativos JSON (IRAM, ISO, ASME) — fuente de verdad |
| `cadnorm/core/` | Modelos Pydantic, carga de perfiles, persistencia SQLite |
| `cadnorm/translators/` | Traductores a formatos CAD (patrón Strategy) |
| `cadnorm/cli/` | Interfaz Typer: `generate`, `profile`, `info` |

### ✨ Características Principales

**Motor normativo**
- ✅ Schema JSON completo con todos los parámetros configurables CAD
- ✅ Perfil IRAM completo: 12 capas, 5 tipos de línea, 5 estilos de texto, escalas normalizadas, formatos A0–A4, rótulo, hachurados

**Generación de archivos (Sprint 2)**
- [ ] AutoCAD `.dwt` con capas, estilos y cotas IRAM
- [ ] LibreCAD `.dxf` compatible

**CLI (Sprint 3)**
- [ ] Wizard interactivo paso a paso
- [ ] Editor de parámetros con advertencias normativas
- [ ] Export/import de perfiles de usuario en JSON

---

## 🚀 Instalación

**Requisitos previos**
- Python 3.11+
- pip

```bash
# Clonar el repositorio
git clone https://github.com/federicoarielcasado/py-project-set.git
cd py-project-set

# Instalar en modo desarrollo (incluye dependencias de test)
pip install -e ".[dev]"
```

### Dependencias Principales

| Paquete | Versión mínima | Uso |
|---------|---------------|-----|
| `ezdxf` | 1.3 | Generación de archivos DXF/DWT |
| `pydantic` | 2.5 | Validación de perfiles normativos |
| `typer` | 0.12 | CLI interactiva |
| `jsonschema` | 4.21 | Validación de JSON contra schema |
| `pytest` | 8.0 | Tests (dev) |
| `pytest-cov` | 5.0 | Cobertura de código (dev) |

---

## 📖 Guía de Uso

### Caso 1: Verificar el POC de ezdxf (Sprint 0)

```bash
# Genera output/minimal_iram.dxf con las capas y estilos IRAM
python scripts/poc_ezdxf.py
```

Salida esperada:
```
============================================================
CADNorm — POC ezdxf
ezdxf version: 1.x.x
============================================================
[1] Cargando perfil IRAM...
    Norma: IRAM v2001
[2] Creando documento DXF R2010...
    OK
[3] Cargando tipos de línea...
    CONTINUOUS: built-in
    DASHED: OK
    ...
[7] Guardando en: output/minimal_iram.dxf
    OK
============================================================
RESUMEN POC
  Capas creadas:          12/12
  Tipos de línea:         5/5
  Estilos de texto:       5/5
  Archivo generado:       minimal_iram.dxf
============================================================
```

### Caso 2: Ejecutar los tests

```bash
pytest
# Con cobertura detallada:
pytest --cov=cadnorm --cov-report=html
```

### Caso 3: Verificar el CLI (esqueleto Sprint 0)

```bash
cadnorm --help
cadnorm generate --norm iram_general --software autocad --output mi_proyecto.dwt
cadnorm info --norm iram_general --category layers
```

---

## 📐 Fundamento Técnico

CADNorm separa **la representación de la norma** (JSON) de **la generación del archivo** (Translator), siguiendo el patrón Strategy:

```
iram_general.json  →  NormProfile  →  AutoCADTranslator  →  proyecto.dwt
                                  →  LibreCADTranslator →  proyecto.dxf
```

Cada traductor implementa el contrato:
```python
def generate(self, profile: NormProfile, output_path: Path) -> GenerationResult: ...
```

Agregar soporte para un nuevo software CAD = crear un nuevo `Translator` sin modificar el núcleo.

---

## 🧩 Arquitectura del Software

```
py-project-set/
├── cadnorm/
│   ├── standards/
│   │   ├── schema.json          ← JSON Schema completo (fuente de verdad)
│   │   └── iram_general.json    ← Datos normativos IRAM
│   ├── core/
│   │   ├── models.py            ← NormProfile (Pydantic en Sprint 1)
│   │   ├── loader.py            ← Carga JSON → NormProfile
│   │   └── db.py                ← Persistencia SQLite (Sprint 1)
│   ├── translators/
│   │   ├── base.py              ← Interfaz abstracta Translator
│   │   ├── autocad.py           ← → .dwt (Sprint 2)
│   │   └── librecad.py          ← → .dxf (Sprint 2)
│   └── cli/
│       └── main.py              ← Typer CLI (Sprint 3)
├── tests/
│   ├── conftest.py
│   └── test_schema.py
├── scripts/
│   └── poc_ezdxf.py             ← POC de validación ezdxf
└── output/                      ← Archivos generados (no versionado)
```

```
Flujo principal:
┌────────────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│  JSON normativo│────▶│  Loader  │────▶│ Translator │────▶│ Archivo  │
│ (iram_*.json)  │     │+ Pydantic│     │ (Strategy) │     │ CAD (.dxf│
└────────────────┘     └──────────┘     └────────────┘     │ / .dwt)  │
                                              ▲             └──────────┘
                              ┌───────────────┤
                              │  CLI wizard   │
                              │  (Typer)      │
                              └───────────────┘
```

---

## 🧪 Testing

```bash
# Todos los tests
pytest

# Con reporte de cobertura HTML
pytest --cov=cadnorm --cov-report=html
# Abrir htmlcov/index.html en el navegador
```

| Test | Descripción | Sprint |
|------|-------------|--------|
| `test_schema_loads_as_json` | schema.json es JSON válido | S0 ✅ |
| `test_schema_has_required_meta_fields` | Campos obligatorios del schema | S0 ✅ |
| `test_schema_defines_all_top_level_sections` | 11 secciones en schema | S0 ✅ |
| `test_iram_profile_validates_against_schema` | iram_general.json cumple el schema | S0 ✅ |
| `test_iram_has_minimum_layers` | ≥ 8 capas en perfil IRAM | S0 ✅ |
| `test_iram_has_normalized_scales` | Escalas 1:1, 1:10, 1:50, 1:100 presentes | S0 ✅ |
| `test_iram_has_all_paper_formats` | Formatos A0–A4 presentes | S0 ✅ |
| `test_iram_title_block_has_required_fields` | Campos de rótulo obligatorios | S0 ✅ |
| `test_units_are_metric` | Sistema métrico, mm | S0 ✅ |

---

## 📚 API Principal

```python
# Cargar perfil normativo built-in
from cadnorm.core.loader import load_builtin_profile
profile = load_builtin_profile("iram_general")

# Cargar perfil personalizado
from cadnorm.core.loader import load_profile
from pathlib import Path
profile = load_profile(Path("mi_perfil_personalizado.json"))

# Interfaz del Translator (Sprint 2)
from cadnorm.translators.base import Translator, GenerationResult
# result = translator.generate(profile, Path("output/proyecto.dwt"))
```

| Clase/Función | Módulo | Descripción |
|---------------|--------|-------------|
| `NormProfile` | `cadnorm.core.models` | Perfil normativo cargado |
| `load_profile(path)` | `cadnorm.core.loader` | Carga JSON → NormProfile |
| `load_builtin_profile(name)` | `cadnorm.core.loader` | Carga perfil incluido en paquete |
| `Translator` | `cadnorm.translators.base` | Interfaz abstracta (Strategy) |
| `GenerationResult` | `cadnorm.translators.base` | Resultado de generación |

---

## 📝 Changelog

### v0.1.0 (16 de Marzo de 2026)

✅ Sprint 0 — Setup inicial:
- ✅ Estructura de directorios del proyecto
- ✅ `pyproject.toml` con stack completo (ezdxf, Pydantic, Typer, pytest)
- ✅ `schema.json` completo con 11 secciones de parámetros CAD
- ✅ `iram_general.json`: 12 capas, 5 tipos de línea, 5 estilos de texto, 14 escalas, 6 formatos, rótulo, 8 hachurados
- ✅ Esqueletos de módulos (`models.py`, `loader.py`, `db.py`, `base.py`, `autocad.py`, `librecad.py`, `main.py`)
- ✅ POC `ezdxf` validado
- ✅ 9 tests pasando (validación schema + perfil IRAM)
- [ ] Sprint 1: Modelos Pydantic completos + validación + SQLite
- [ ] Sprint 2: Generación .dwt/.dxf con ezdxf
- [ ] Sprint 3: CLI wizard + editor de parámetros + perfiles de usuario

---

## 📄 Licencia

[MIT License](LICENSE) — Copyright (c) 2026 Federico Casado

---

## 👨‍💻 Autor

**Federico Casado** — Ingeniero Civil | Python Developer | Argentina
Stack: Python · CAD/BIM · Automatización técnica · Open source

---
*Última actualización: 16 de Marzo de 2026*
