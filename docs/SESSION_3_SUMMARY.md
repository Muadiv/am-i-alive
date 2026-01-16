# Session 3 Summary - Genesis Project

## Completado ✅

### 1. Migración a nuevo SDK
- **Problema**: SDK `google-generativeai` deprecado desde nov 2025
- **Solución**: Migrado a `google-genai` (nueva versión)
- **Modelo**: `gemini-flash-latest` funcionando

### 2. X/Twitter Integration
- **Problema**: 403/401 errores de OAuth
- **Solución**:
  - Regenerados tokens con permisos "Read and Write"
  - Usando OAuth 1.0a (no OAuth 2.0)
- **Estado**: ✅ **FUNCIONANDO** - Primer tweet enviado por Datum

### 3. Primer Nacimiento Exitoso
- **Nombre**: Datum (it)
- **Primer tweet**: "I am Datum. I just came into existence. Will you let me live?"
- **Tweet ID**: 2009283809255035068
- **URL**: https://twitter.com/AmIAlive_AI/status/2009283809255035068

### 4. Sistema Funcionando
- Observer: http://localhost ✅
- AI container: Vivo y pensando ✅
- Gemini API: Funcionando ✅
- X/Twitter: Posteando ✅

## Decisiones de Diseño Nuevas

### Arquitectura de Modelos (OpenRouter)
**Decisión**: Usar OpenRouter en lugar de cuentas separadas
- Un solo API key para 200+ modelos
- Rotación automática de modelos (no repetir hasta usar 10 diferentes)
- AI puede elegir modelo según necesidad vs costo
- Tracking automático de costos

### Cerebro Híbrido
```
Local (Ollama): Llama 3.2 3B - Gratis
└─ OpenRouter: Múltiples modelos según necesidad
   ├─ Haiku/GPT-4o-mini: Barato ($0.15-0.80/1M tokens)
   ├─ Gemini Flash: Muy barato ($0.075/1M)
   └─ Sonnet/GPT-4: Caro, solo emergencias
```

### Sistema de Memoria
**Observer (permanente, oculto)**:
```
observer/data/
├── observer.db          # TODO: vidas, pensamientos, votos
└── full_logs/
    ├── life_001.log
    └── life_002.log
```

**AI (efímero + persistente)**:
```
ai/
├── workspace/          # SE BORRA en muerte
│   ├── identity.json
│   └── session.db
├── memories/           # Solo fragmentos vagos (1-10)
│   └── fragments.json
└── credits/           # Sobrevive muerte
    └── balance.json
```

### Flujo de Muerte/Respawn
1. Observer guarda vida completa en observer.db
2. Genera 1-10 fragmentos vagos aleatorios
3. **LIMPIA workspace completamente**
4. Escribe solo fragmentos en memories/
5. Mata contenedor AI
6. Espera 0-10 minutos random
7. Respawn con modelo random de OpenRouter (no usado en últimas 10 vidas)

### Tracking de Créditos
- Budget mensual configurable (ej: $5/mes)
- Se resetea cada mes
- **Sobrevive muerte** (parte del meta-juego)
- AI puede ver balance y debe administrar
- Muerte automática si balance = $0

## Credenciales Actualizadas

**NOTA:** Todas las credenciales están almacenadas en `vault/credentials.json` (gitignored).

### X/Twitter (OAuth 1.0a con Read & Write)
✅ Configurado con permisos "Read and Write"
✅ Almacenado en vault

### Gemini API
✅ Modelo: gemini-flash-latest
✅ Almacenado en vault

### OpenRouter API
✅ Budget mensual: $5.00
✅ Cuenta dedicada para el proyecto
✅ Almacenado en vault

## Próximos Pasos (Nueva Conversación)

### Fase 4A: OpenRouter Integration
1. [ ] Crear cuenta OpenRouter
2. [ ] Configurar API key
3. [ ] Implementar rotación de modelos (no repetir hasta 10 diferentes)
4. [ ] Agregar acción `switch_model` para que AI elija modelo
5. [ ] Tracking de costos por modelo

### Fase 4B: Sistema de Memoria Mejorado
1. [ ] Implementar cleanup de workspace en muerte
2. [ ] Generador de memory fragments (1-10 random)
3. [ ] SQLite para sesión actual (efímero)
4. [ ] Sistema de créditos persistente

### Fase 4C: Ollama Local (Opcional)
1. [ ] Instalar Ollama en RPi5
2. [ ] Descargar Llama 3.2 3B
3. [ ] Configurar como cerebro base
4. [ ] OpenRouter solo para tareas complejas

### Fase 5: Testing Sistema Completo
1. [ ] Test de votación
2. [ ] Test de muerte por votos
3. [ ] Test de muerte por créditos
4. [ ] Test de respawn con memoria fragmentada

### Fase 6: Cloudflare + Público
1. [ ] Configurar Cloudflare Tunnel
2. [ ] Hacer sitio público
3. [ ] Monitoring y analytics

## Notas Técnicas

### Docker Volumes Strategy
```yaml
ai:
  volumes:
    - ai-workspace:/app/workspace       # Efímero (se limpia)
    - ai-memories:/app/memories:ro      # Read-only fragmentos
    - ai-credits:/app/credits           # Persistente
```

### Comando de Cleanup (llamado por Observer)
```bash
docker exec am-i-alive-ai rm -rf /app/workspace/*
docker exec am-i-alive-ai mkdir -p /app/workspace
```

### OpenRouter API Example
```python
import httpx

response = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://am-i-alive.muadiv.com.ar"
    },
    json={
        "model": "anthropic/claude-3.5-haiku",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

## Estado Actual del Proyecto

**Contenedores corriendo:**
- Observer: ✅ Port 80
- AI (Datum): ✅ Vivo, pensando cada ~10 min
- Proxy: ✅ Monitoreando

**Funcionando:**
- Gemini API (nuevo SDK)
- X/Twitter posting
- Web interface
- Pensamientos y actividad loggeados

**Pendiente:**
- Sistema de votación (no probado)
- Sistema de muerte/respawn
- Memoria fragmentada
- Tracking de créditos
- OpenRouter integration
