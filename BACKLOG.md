# Virtual Mouse — Memoria del proyecto y backlog

Última actualización: 2026-07-28

Documento de referencia para retomar el proyecto: estado actual, decisiones, y mejoras pendientes.

---

## 1. Qué es

App de **mouse virtual por gestos** con webcam + MediaPipe Hands + OpenCV + PyAutoGUI.
Controla cursor, clics, drag, scroll y pausa sin tocar el mouse físico.

Repo: https://github.com/Nahuelito22/Virtual_Mouse  
Entrada principal: `virtual_mouse.py`

---

## 2. Estado actual (hecho)

### App (`virtual_mouse.py`)
- [x] Arquitectura por clases (`VirtualMouse`, `Config`, `Mode`, `GestureCooldown`)
- [x] Movimiento con suavizado + ROI (`frame_reduction`)
- [x] Clic izquierdo (pellizco pulgar+índice) con cooldown
- [x] Drag & drop (mantener pellizco izquierdo)
- [x] Doble clic (pulgar+medio)
- [x] Clic derecho (pulgar+anular)
- [x] Scroll (índice+medio arriba)
- [x] Pausa (puño) / reanudar (mano abierta)
- [x] Salir con hold pulgar+meñique + barra de progreso
- [x] Detección mano izq/der (imagen espejada)
- [x] UI: FPS, modo, panel ayuda, mensajes de estado
- [x] Teclas: `Q` salir, `H` ayuda, `L` landmarks, `+/-` suavizado, `C` cámara
- [x] CLI: `--camera`, `--list-cameras`, `--pick-camera`, `--smooth`, `--pinch`, etc.
- [x] Selector visual de cámara con vista previa en vivo
- [x] Preferencia de cámara guardada en `~/.virtual_mouse/config.json`
- [x] Manejo de error de cámara + cleanup de recursos

### Empaquetado y DX
- [x] `requirements.txt` con rangos de versión
- [x] `build.ps1` → genera `Release/AI_Virtual_Mouse.exe` (PyInstaller)
- [x] `run.bat` launcher (prioriza venv Python)
- [x] `AI_Virtual_Mouse.spec`
- [x] README actualizado (gestos, cámara, teclas, build)
- [x] `.gitignore` (venv, build, Release, exe)

### Hardware detectado en dev (referencia)
- `[0] Logi C270 HD WebCam` — webcam correcta
- `[1] HP DeskJet...` — impresora (no usar)
- Nota: en otras PCs el índice 0 puede ser Phone Link / celular virtual

### Versiones conocidas (venv local)
- Python 3.12
- OpenCV 4.11, MediaPipe 0.10.21, PyAutoGUI 0.9.54, NumPy 1.26 (`numpy<2`)

---

## 3. Cómo usar (rápido)

```bat
run.bat --list-cameras
run.bat --pick-camera
run.bat -c 0
python virtual_mouse.py
.\build.ps1
```

Config cámara: `%USERPROFILE%\.virtual_mouse\config.json`

---

## 4. Backlog — mejoras futuras

### Prioridad alta
- [ ] **Rebuild del .exe** tras cambios de cámara (`.\build.ps1`) y opcional GitHub Release
- [ ] **Calibración de umbral de pellizco** en UI (slider o teclas `[` `]`)
- [ ] **Modo sin ventana de cámara** (solo HUD mínimo / bandeja del sistema) para no tapar trabajo
- [ ] **Mejor mapeo nombre↔índice DirectShow** (pygrabber o COM) en vez de heurística WMI
- [ ] **Tests unitarios** de gestos/cooldown con landmarks sintéticos (sin cámara)

### Prioridad media — gestos y control
- [ ] **Zoom** (pellizco dos manos o gesto dedicado)
- [ ] **Alt-Tab / cambiar ventana** con gesto
- [ ] **Volumen / multimedia** (media keys)
- [ ] **Click-and-hold vs drag** más configurable (tiempos en config)
- [ ] **Sensibilidad de scroll** ajustable en caliente
- [ ] **Perfiles de gestos** (trabajo / presentaciones / accesibilidad)
- [ ] **Mano dominante** configurable sin depender solo de MediaPipe
- [ ] **Filtro One Euro / Kalman** en vez de solo lerp para menos jitter con menos lag

### Prioridad media — UX / producto
- [ ] **Overlay on-screen** de gestos activos (siempre visible, semi-transparente)
- [ ] **Sonido/feedback** opcional al clic
- [ ] **Primera ejecución wizard**: listar cámaras + tutorial de gestos
- [ ] **Icono de app** en el .exe (`.ico`)
- [ ] **Atajo global** para pausar/reanudar sin foco en la ventana OpenCV
- [ ] **Idioma** ES/EN en UI
- [ ] **Tema UI** más pulido (OpenCV limitado; valorar Dear PyGui / customtkinter para settings)

### Prioridad baja — técnica
- [ ] Migrar a **MediaPipe Tasks** (API nueva) cuando estabilice en Windows
- [ ] Soporte **Linux/macOS** documentado y probado
- [ ] **GPU / rendimiento**: bajar resolución de proceso si FPS < 20
- [ ] Log a archivo opcional (`--verbose` / `--log`)
- [ ] CI GitHub Actions: lint + py_compile + artifact del exe (Windows runner)
- [ ] Versionado semántico + changelog (`CHANGELOG.md`)
- [ ] Firma del .exe / SmartScreen (opcional, coste)

### Ideas exploratorias
- [ ] Control con **ojos / cabeza** (accesibilidad)
- [ ] Modo **presentador** (láser virtual + avance de diapositivas)
- [ ] Integración con **stream decks** / OBS
- [ ] Entrenar clasificador de gestos custom (si MediaPipe se queda corto)

---

## 5. Deuda técnica conocida

1. Nombres de cámara vía WMI no siempre coinciden 1:1 con índices OpenCV/DirectShow.
2. `.exe` ~230 MB (MediaPipe + deps); no se versiona en git (`Release/` ignorado).
3. PyInstaller windowed: errores de cámara poco visibles sin consola; valorar build con consola debug.
4. Thumb detection sigue sensible a ángulo de la mano y espejo.
5. Clic en release del pellizco: si el usuario “tiembla” el umbral, puede fallar o doble-disparar (mitigado con cooldown).
6. `numpy<2` por compatibilidad con el stack actual de MediaPipe.

---

## 6. Decisiones de diseño

| Decisión | Motivo |
| :--- | :--- |
| Un solo `virtual_mouse.py` | Proyecto personal simple de mantener |
| Cooldown en clics | Evitar spam de `pyautogui.click` por frame |
| Drag = hold del pellizco izq | Un solo gesto, dos acciones (tap vs hold) |
| Salir con hold | Evitar cierre accidental con meñique |
| Guardar cámara en home | Persiste entre sesiones sin ensuciar el repo |
| Selector visual | Usuario ve webcam vs celular/virtual |
| No commitear el .exe | Binario grande; se regenera con `build.ps1` |

---

## 7. Archivos clave

```
virtual_mouse.py       App completa
requirements.txt       Deps
build.ps1              Build Windows exe
run.bat                Launcher
AI_Virtual_Mouse.spec  PyInstaller
README.md              Documentación usuario
BACKLOG.md             Este archivo (memoria + backlog)
assets/                Capturas README
```

---

## 8. Próximo paso sugerido al retomar

1. Probar selector de cámara en la máquina del usuario (`run.bat --pick-camera`).
2. Si todo OK → `.\build.ps1` y publicar Release en GitHub con el exe.
3. Luego: calibración de pinch en UI + modo “solo bandeja” sin ventana grande.
