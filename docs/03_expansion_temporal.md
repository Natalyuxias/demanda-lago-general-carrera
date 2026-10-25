# 03. Sensibilidades de 10 a24 horas

Los conteos terrestres usados representan10 h, no un día completo. Primavera utiliza08–18 y verano/mayo09–19 según exposición reconstruida. No se siguió buscando factores después de la etapa 08.

MOP publica coeficientes generales12→24 h: verano 1,46, invierno 1,29, primavera 1,35. **No son factores10→24 h.** Las tablas CITRA revisadas describen períodos diurnos parciales, no una estación comparable de24 h para Cerro Castillo. No se digitalizaron gráficos cuando había tabla.

Se construyó una sensibilidad híbrida:

`F_10_24 = (Q_perfil_07_19 / Q_perfil_ventana10h_ARISTO) × F_MOP_12_24`.

El primer cociente permite adaptar ventanas. No demuestra la representatividad del perfil urbano ni valida un factor oficial10 h. Los perfiles publicados usan vehículos equivalentes; se transfiere la forma horaria a VL como supuesto, sin convertir veq en vehículos físicos.

| perfil | estacion_destino | ventana_ARISTO | relacion_12h_10h | coeficiente_MOP_12_24 | factor_24h_10h_sensibilidad |
| --- | --- | --- | --- | --- | --- |
| CC_PC1_laboral | Primavera | 08:00-18:00 | 1.16187 | 1.35 | 1.56852 |
| CC_PC1_laboral | Verano | 09:00-19:00 | 1.13134 | 1.46 | 1.65176 |
| CC_PC2_laboral | Primavera | 08:00-18:00 | 1.22244 | 1.35 | 1.65029 |
| CC_PC2_laboral | Verano | 09:00-19:00 | 1.16342 | 1.46 | 1.69859 |
| CC_PC3_mov24_laboral | Primavera | 08:00-18:00 | 1.22885 | 1.35 | 1.65895 |
| CC_PC3_mov24_laboral | Verano | 09:00-19:00 | 1.21781 | 1.46 | 1.77801 |
| CC_PC3_mov42_laboral | Primavera | 08:00-18:00 | 1.20537 | 1.35 | 1.62725 |
| CC_PC3_mov42_laboral | Verano | 09:00-19:00 | 1.16775 | 1.46 | 1.70492 |

`Q_OD_24h=Q_OD_10h×F`. Se conserva la composición OD dentro del estrato como hipótesis. Reproducir un control expandido no valida estadísticamente cadaOD. Se contrastanPC1,PC2 y movimientos separados dePC3; no se corrige silenciosamente la columna Total inconsistente dePC3.

El caso base24 h observado permanece faltante. No hay coeficiente otoñal compatible ni campaña invernal suficiente; la calibración central VL 24 h se restringe al soporte disponible. CAM conserva contraste10 h, sin inventar factor24 h por clase. No se anualiza ni se calcula TMDA.

Fuentes: CITRA Informe 1 cuadros38–44 pp167–175 y MOP/PNCV; manifiestos y transcripciones detallados solo en `outputs/expansion_temporal_terrestre/`. Los CSV compartidos contienen cocientes calculados, no las tablas originales.
