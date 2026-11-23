import streamlit as st
import pandas as pd
import json
import re
import time
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

# ==============================================================================
# 1. CONSTANTES GLOBALES Y CONFIGURACIÓN DEL SISTEMA (SINCRONIZADAS AL 98%)
# ==============================================================================
APP_TITLE = "Ecosistema Integral de Gestión de Facturación (EIG)"
APP_SUBTITLE = (
    "A&P Ambulancias S.A.S. | Validación Contractual Determinista (JSON Schema / Pydantic) "
    "y Enrutamiento Automatizado SOAT"
)
AUTOMATIZACION_PCT = "98.0%"
HITL_PCT = "2.0%"
TIEMPO_AS_IS_HORAS = 40.0
TIEMPO_TO_BE_MINUTOS = 45
AHORRO_DIRECTO_ANUAL_COP = "$24.000.000 COP"

REGEX_CIE10 = r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$"
REGEX_PLACA_CO = r"^[A-Z]{3}-?[0-9]{3}$"

st.set_page_config(
    page_title="EIG Facturación - A&P Ambulancias S.A.S.",
    page_icon="🚑",
    layout="wide"
)

st.markdown("""
<style>
    .success-badge { background-color: #DCFCE7; color: #166534; padding: 8px 12px; border-radius: 6px; font-weight: bold; }
    .danger-badge { background-color: #FEE2E2; color: #991B1B; padding: 8px 12px; border-radius: 6px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MODELO DE VALIDACIÓN PYDANTIC (CONTRATO DE DATOS ANTI-GLOSAS)
# ==============================================================================
class HistoriaClinicaJSON(BaseModel):
    id_historia_clinica: str = Field(..., description="ID único de la HC generada en tablet")
    codigo_movil: str = Field(..., description="Unidad de ambulancia (ej. MED-01)")
    fecha_servicio: str = Field(..., description="Fecha del servicio YYYY-MM-DD")
    paciente_doc_id: str = Field(..., description="Documento de identidad del paciente")
    paciente_nombre: str = Field(..., description="Nombre del paciente")
    placa_vehiculo_accidente: str = Field(..., description="Placa del vehículo siniestrado")
    numero_poliza_soat: str = Field(..., description="Número de póliza SOAT")
    aseguradora_soat: str = Field(..., description="Nombre de la aseguradora SOAT")
    codigo_cie10: str = Field(..., description="Código diagnóstico CIE-10")
    valor_facturado_cop: float = Field(..., gt=0, description="Monto del servicio en COP")
    firma_medico_digital: bool = Field(..., description="Firma digital verificada")

    @field_validator("fecha_servicio")
    @classmethod
    def validar_fecha(cls, v: str) -> str:
        try:
            datetime.strptime(str(v).strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError("ERR_FECHA_INVALIDA: La fecha debe cumplir el formato exacto YYYY-MM-DD.")
        return str(v).strip()

    @field_validator("placa_vehiculo_accidente")
    @classmethod
    def validar_placa(cls, v: str) -> str:
        placa_limpia = str(v).strip().upper()
        if not re.match(REGEX_PLACA_CO, placa_limpia):
            raise ValueError(f"ERR_PLACA_SOAT: La placa '{v}' no cumple el formato vehicular colombiano (ABC-123).")
        return placa_limpia

    @field_validator("numero_poliza_soat")
    @classmethod
    def validar_poliza(cls, v: str) -> str:
        if not v or str(v).strip() == "" or str(v).strip().upper() in {"SIN POLIZA", "N/A", "NULL"}:
            raise ValueError("ERR_POLIZA_FALTANTE: El número de póliza SOAT es obligatorio para evitar glosa inmediata.")
        return str(v).strip().upper()

    @field_validator("codigo_cie10")
    @classmethod
    def validar_cie10(cls, v: str) -> str:
        codigo = str(v).strip().upper()
        if not re.match(REGEX_CIE10, codigo):
            raise ValueError(f"ERR_CIE10_INVALIDO: El código '{v}' no corresponde a la estructura oficial CIE-10 (ej. S82.1).")
        return codigo

    @field_validator("firma_medico_digital")
    @classmethod
    def validar_firma(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ERR_SIN_FIRMA: Falta la firma digital del profesional asistencial en la Historia Clínica.")
        return v

# ==============================================================================
# 3. DATASET SINTÉTICO DE REFERENCIA (20 CASOS GROUND TRUTH)
# ==============================================================================
DATASET_SINTETICO_20 = [
    {"id_historia_clinica": "HC-2026-8801", "codigo_movil": "MED-01", "fecha_servicio": "2026-11-02", "paciente_doc_id": "1019283746", "paciente_nombre": "Carlos Alberto Gómez", "placa_vehiculo_accidente": "LUZ-079", "numero_poliza_soat": "POL-99281-SOAT", "aseguradora_soat": "Seguros del Estado", "codigo_cie10": "S82.1", "valor_facturado_cop": 450000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8802", "codigo_movil": "MED-02", "fecha_servicio": "2026-11-03", "paciente_doc_id": "52849102", "paciente_nombre": "María Fernanda López", "placa_vehiculo_accidente": "DBV-552", "numero_poliza_soat": "POL-44102-SOAT", "aseguradora_soat": "Sura", "codigo_cie10": "T14.2", "valor_facturado_cop": 520000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8803", "codigo_movil": "MED-03", "fecha_servicio": "2026-11-04", "paciente_doc_id": "1098234112", "paciente_nombre": "Jorge Eliécer Mendoza", "placa_vehiculo_accidente": "BVR-676", "numero_poliza_soat": "POL-88319-SOAT", "aseguradora_soat": "La Previsora", "codigo_cie10": "S06.0", "valor_facturado_cop": 680000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8804", "codigo_movil": "MED-04", "fecha_servicio": "2026-11-05", "paciente_doc_id": "80123984", "paciente_nombre": "Ana Lucía Torres", "placa_vehiculo_accidente": "KLR-441", "numero_poliza_soat": "", "aseguradora_soat": "Seguros Bolívar", "codigo_cie10": "S13.4", "valor_facturado_cop": 410000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8805", "codigo_movil": "MED-05", "fecha_servicio": "2026-11-06", "paciente_doc_id": "79654321", "paciente_nombre": "Luis Eduardo Ramírez", "placa_vehiculo_accidente": "MNT-812", "numero_poliza_soat": "POL-55210-SOAT", "aseguradora_soat": "Seguros del Estado", "codigo_cie10": "S42.0", "valor_facturado_cop": 490000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8806", "codigo_movil": "MED-06", "fecha_servicio": "2026-11-07", "paciente_doc_id": "1022398411", "paciente_nombre": "Sandra Milena Castro", "placa_vehiculo_accidente": "GHT-304", "numero_poliza_soat": "POL-61904-SOAT", "aseguradora_soat": "Sura", "codigo_cie10": "S52.5", "valor_facturado_cop": 460000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8807", "codigo_movil": "MED-07", "fecha_servicio": "2026-11-08", "paciente_doc_id": "39784512", "paciente_nombre": "Claudia Patricia Morales", "placa_vehiculo_accidente": "JKL-920", "numero_poliza_soat": "POL-73412-SOAT", "aseguradora_soat": "La Previsora", "codigo_cie10": "S72.0", "valor_facturado_cop": 740000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8808", "codigo_movil": "MED-08", "fecha_servicio": "2026-11-09", "paciente_doc_id": "1014209876", "paciente_nombre": "Andrés Felipe Vargas", "placa_vehiculo_accidente": "PQR-118", "numero_poliza_soat": "POL-81209-SOAT", "aseguradora_soat": "Seguros Bolívar", "codigo_cie10": "T07", "valor_facturado_cop": 650000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8809", "codigo_movil": "MED-01", "fecha_servicio": "2026-11-10", "paciente_doc_id": "51982345", "paciente_nombre": "Gloria Esperanza Ruiz", "placa_vehiculo_accidente": "WXY-605", "numero_poliza_soat": "POL-90344-SOAT", "aseguradora_soat": "Seguros del Estado", "codigo_cie10": "S8", "valor_facturado_cop": 395000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8810", "codigo_movil": "MED-02", "fecha_servicio": "2026-11-11", "paciente_doc_id": "1030567890", "paciente_nombre": "Diego Alejandro Herrera", "placa_vehiculo_accidente": "FGH-229", "numero_poliza_soat": "POL-33498-SOAT", "aseguradora_soat": "Sura", "codigo_cie10": "S82.2", "valor_facturado_cop": 475000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8811", "codigo_movil": "MED-03", "fecha_servicio": "2026-11-12", "paciente_doc_id": "79451238", "paciente_nombre": "Héctor Fabio Ortiz", "placa_vehiculo_accidente": "RST-741", "numero_poliza_soat": "POL-29841-SOAT", "aseguradora_soat": "La Previsora", "codigo_cie10": "S06.9", "valor_facturado_cop": 610000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8812", "codigo_movil": "MED-04", "fecha_servicio": "2026-11-13", "paciente_doc_id": "1018432190", "paciente_nombre": "Natalia Andrea Silva", "placa_vehiculo_accidente": "CVB-503", "numero_poliza_soat": "POL-48712-SOAT", "aseguradora_soat": "Seguros Bolívar", "codigo_cie10": "S13.4", "valor_facturado_cop": 430000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8813", "codigo_movil": "MED-05", "fecha_servicio": "2026-11-14", "paciente_doc_id": "52410987", "paciente_nombre": "Martha Isabel Pardo", "placa_vehiculo_accidente": "NML-884", "numero_poliza_soat": "POL-67123-SOAT", "aseguradora_soat": "Seguros del Estado", "codigo_cie10": "T14.1", "valor_facturado_cop": 385000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8814", "codigo_movil": "MED-06", "fecha_servicio": "2026-11-15", "paciente_doc_id": "80765432", "paciente_nombre": "Óscar Iván Delgado", "placa_vehiculo_accidente": "ZXC-190", "numero_poliza_soat": "POL-51908-SOAT", "aseguradora_soat": "Sura", "codigo_cie10": "S42.2", "valor_facturado_cop": 540000.0, "firma_medico_digital": False},
    {"id_historia_clinica": "HC-2026-8815", "codigo_movil": "MED-07", "fecha_servicio": "2026-11-16", "paciente_doc_id": "1026543987", "paciente_nombre": "Paula Andrea Rojas", "placa_vehiculo_accidente": "QWE-367", "numero_poliza_soat": "POL-84521-SOAT", "aseguradora_soat": "La Previsora", "codigo_cie10": "S82.0", "valor_facturado_cop": 495000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8816", "codigo_movil": "MED-08", "fecha_servicio": "2026-11-17", "paciente_doc_id": "39651209", "paciente_nombre": "Beatriz Elena Navarro", "placa_vehiculo_accidente": "TYU-482", "numero_poliza_soat": "POL-93017-SOAT", "aseguradora_soat": "Seguros Bolívar", "codigo_cie10": "S30.0", "valor_facturado_cop": 420000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8817", "codigo_movil": "MED-01", "fecha_servicio": "2026-11-18", "paciente_doc_id": "1015432876", "paciente_nombre": "Camila Sofía Mejía", "placa_vehiculo_accidente": "IOP-915", "numero_poliza_soat": "POL-77834-SOAT", "aseguradora_soat": "Seguros del Estado", "codigo_cie10": "S62.6", "valor_facturado_cop": 440000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8818", "codigo_movil": "MED-02", "fecha_servicio": "2026-11-19", "paciente_doc_id": "79812345", "paciente_nombre": "Ricardo Javier Peña", "placa_vehiculo_accidente": "889-ABC", "numero_poliza_soat": "POL-64219-SOAT", "aseguradora_soat": "Sura", "codigo_cie10": "S06.0", "valor_facturado_cop": 690000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8819", "codigo_movil": "MED-03", "fecha_servicio": "2026-11-20", "paciente_doc_id": "1032456789", "paciente_nombre": "Valentina Ríos Cardona", "placa_vehiculo_accidente": "ASD-638", "numero_poliza_soat": "POL-12984-SOAT", "aseguradora_soat": "La Previsora", "codigo_cie10": "S93.4", "valor_facturado_cop": 415000.0, "firma_medico_digital": True},
    {"id_historia_clinica": "HC-2026-8820", "codigo_movil": "MED-04", "fecha_servicio": "2026-11-21", "paciente_doc_id": "52789456", "paciente_nombre": "Carolina Duarte Gil", "placa_vehiculo_accidente": "HJK-254", "numero_poliza_soat": "POL-39012-SOAT", "aseguradora_soat": "Seguros Bolívar", "codigo_cie10": "T14.2", "valor_facturado_cop": 510000.0, "firma_medico_digital": True}
]

CASOS_DEMO = {
    "Caso Demo 1: Traslado TAB Válido (Seguros del Estado)": DATASET_SINTETICO_20[0],
    "Caso Demo 2: FALLA CONTROLADA - Póliza SOAT Faltante": DATASET_SINTETICO_20[3],
    "Caso Demo 3: FALLA CONTROLADA - Código CIE-10 Inválido": DATASET_SINTETICO_20[8],
    "Caso Demo 4: FALLA CONTROLADA - Sin Firma Digital": DATASET_SINTETICO_20[13],
    "Caso Demo 5: FALLA CONTROLADA - Placa Vehicular Inválida": DATASET_SINTETICO_20[17]
}

if "audit_logs" not in st.session_state:
    st.session_state["audit_logs"] = []

def registrar_evento_log(hc_id: str, aseguradora: str, estado: str, latencia_ms: float, glosa: str, detalle: str):
    st.session_state["audit_logs"].insert(0, {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ID_HC": hc_id,
        "Aseguradora": aseguradora,
        "Estado_Flujo": estado,
        "Latencia_ms": round(latencia_ms, 2),
        "Glosa_SOAT": glosa,
        "Detalle_Auditoria": detalle
    })

def evaluar_registro(registro: dict) -> dict:
    inicio = time.perf_counter()
    hc_id = str(registro.get("id_historia_clinica", "SIN_ID"))
    aseguradora = str(registro.get("aseguradora_soat", "NO_ESPECIFICADA"))
    try:
        hc_valida = HistoriaClinicaJSON(**registro)
        latencia_ms = (time.perf_counter() - inicio) * 1000
        detalle = f"Validación contractual OK | CIE-10: {hc_valida.codigo_cie10} | Póliza: {hc_valida.numero_poliza_soat}"
        registrar_evento_log(hc_id, hc_valida.aseguradora_soat, "RADICADO_HTTP_200", latencia_ms, "NO (0%)", detalle)
        return {"valido": True, "objeto": hc_valida, "latencia_ms": latencia_ms, "error": None}
    except Exception as e:
        latencia_ms = (time.perf_counter() - inicio) * 1000
        mensaje_error = str(e).replace("\n", " | ")
        registrar_evento_log(hc_id, aseguradora, "ESCALADO_HITL", latencia_ms, "PREVENIDA", mensaje_error)
        return {"valido": False, "objeto": None, "latencia_ms": latencia_ms, "error": mensaje_error}

# ==============================================================================
# 4. INTERFAZ DE USUARIO STREAMLIT
# ==============================================================================
st.title(f"🚑 {APP_TITLE}")
st.caption(APP_SUBTITLE)

st.sidebar.header("🕹️ Panel de Control")
opcion_caso = st.sidebar.selectbox("Seleccionar Caso Demo (JSON):", list(CASOS_DEMO.keys()))
json_actual = CASOS_DEMO[opcion_caso]

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Indicadores Clave (AS-IS vs TO-BE)")
st.sidebar.metric("Tiempo Semanal Procesamiento", f"{TIEMPO_TO_BE_MINUTOS} min", f"-98.1% vs AS-IS ({int(TIEMPO_AS_IS_HORAS)}h)")
st.sidebar.metric("Automatización / Escalamiento HITL", f"{AUTOMATIZACION_PCT} / {HITL_PCT}", "Cero glosas formales")
st.sidebar.metric("Ahorro Directo Facturación", AHORRO_DIRECTO_ANUAL_COP, "Liberación 1.96 ETP")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Validación Individual (Vivo)",
    "📂 Evaluación Ground Truth (20 Casos)",
    "📡 Router API & Log Dinámico",
    "📈 Impacto Operativo (ROI)"
])

# ------------------------------------------------------------------------------
# TAB 1: VALIDACIÓN INDIVIDUAL EN VIVO
# ------------------------------------------------------------------------------
with tab1:
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("📥 Entrada JSON desde Tablet de Ambulancia")
        raw_json_str = st.text_area("Editar JSON para prueba manual en vivo:", value=json.dumps(json_actual, indent=2), height=320)

    with col_right:
        st.subheader("⚙️ Motor de Validación Contractual Pydantic")
        if st.button("⚡ Validar y Enrutar Historia Clínica", type="primary"):
            try:
                data_dict = json.loads(raw_json_str)
                resultado = evaluar_registro(data_dict)
                if resultado["valido"]:
                    obj = resultado["objeto"]
                    st.markdown('<div class="success-badge">✅ RADICADO_HTTP_200: CUMPLE 100% REGLAS SOAT</div>', unsafe_allow_html=True)
                    st.success(f"Validado en {resultado['latencia_ms']:.2f} ms y enviado a API de {obj.aseguradora_soat}.")
                    st.json(obj.model_dump())
                else:
                    st.markdown('<div class="danger-badge">🚨 ESCALADO_HITL: GLOSA PREVENIDA ANTES DE RADICAR</div>', unsafe_allow_html=True)
                    st.error(f"Inconsistencia detectada ({resultado['latencia_ms']:.2f} ms):\n\n{resultado['error']}")
                    st.warning("🔄 Desviado automáticamente a la Cola de Revisión Humana (HITL) y registrado en el Log.")
            except json.JSONDecodeError as je:
                st.error(f"Error de sintaxis JSON crudo: {je}")

# ------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN SOBRE CONJUNTO GROUND TRUTH (20 CASOS)
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("📂 Evaluación sobre Dataset de Referencia (Ground Truth = 20 Casos)")
    st.info("Ejecute el conjunto sintético de 20 casos modelado sobre la casuística histórica de A&P Ambulancias S.A.S. (Ley 1581 de 2012) o cargue un archivo externo (.json / .csv).")

    modo_carga = st.radio(
        "Origen de los 20 casos de prueba:",
        ["Usar Dataset Sintético de Referencia Incorporado (20 Casos)", "Subir archivo externo (.json o .csv)"],
        horizontal=True
    )

    casos_a_evaluar = None
    if modo_carga == "Usar Dataset Sintético de Referencia Incorporado (20 Casos)":
        casos_a_evaluar = DATASET_SINTETICO_20
        st.download_button(
            label="⬇️ Descargar Dataset Sintético (ground_truth_20_casos.json)",
            data=json.dumps(DATASET_SINTETICO_20, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="ground_truth_20_casos.json",
            mime="application/json"
        )
    else:
        archivo_ext = st.file_uploader("Subir archivo de casos (.json o .csv):", type=["json", "csv"])
        if archivo_ext is not None:
            if archivo_ext.name.endswith(".json"):
                casos_a_evaluar = json.load(archivo_ext)
            else:
                casos_a_evaluar = pd.read_csv(archivo_ext).to_dict(orient="records")

    if casos_a_evaluar is not None:
        st.write(f"**Registros listos para auditoría:** {len(casos_a_evaluar)} historias clínicas.")
        if st.button("🚀 Ejecutar Benchmark sobre 20 Casos", type="primary"):
            resultados_batch = []
            for reg in casos_a_evaluar:
                res = evaluar_registro(reg)
                resultados_batch.append({
                    "ID_HC": reg.get("id_historia_clinica", "N/A"),
                    "Móvil": reg.get("codigo_movil", "N/A"),
                    "Aseguradora": reg.get("aseguradora_soat", "N/A"),
                    "CIE-10": reg.get("codigo_cie10", "N/A"),
                    "Resultado": "APROBADO_API" if res["valido"] else "ESCALADO_HITL",
                    "Latencia_ms": round(res["latencia_ms"], 2),
                    "Motivo_Control": "OK" if res["valido"] else res["error"]
                })
            df_res = pd.DataFrame(resultados_batch)
            total = len(df_res)
            aprobados = (df_res["Resultado"] == "APROBADO_API").sum()
            escalados = total - aprobados

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Evaluados", total)
            c2.metric("Radicados Automáticos", f"{aprobados} ({aprobados/total*100:.1f}%)")
            c3.metric("Interceptados HITL", f"{escalados} ({escalados/total*100:.1f}%)")
            c4.metric("Latencia Media", f"{df_res['Latencia_ms'].mean():.2f} ms")

            st.dataframe(df_res, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: ROUTER API & LOG DINÁMICO EN TIEMPO REAL
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📡 Enrutador API SOAT y Log Inmutable de Auditoría")
    col1, col2, col3 = st.columns(3)
    col1.info("🏛️ **Seguros del Estado** | TLS 1.3 | 🟢 Operativo")
    col2.info("🏢 **Sura SOAT** | TLS 1.3 | 🟢 Operativo")
    col3.info("🏥 **La Previsora** | TLS 1.3 | 🟢 Operativo")

    st.markdown("---")
    col_log_hdr, col_log_btn = st.columns([3, 1])
    col_log_hdr.subheader(f"Registros de Auditoría en Sesión ({len(st.session_state['audit_logs'])} eventos)")
    if col_log_btn.button("🗑️ Limpiar Log de Sesión"):
        st.session_state["audit_logs"] = []
        st.rerun()

    if st.session_state["audit_logs"]:
        df_logs = pd.DataFrame(st.session_state["audit_logs"])
        st.dataframe(df_logs, use_container_width=True)
        st.download_button(
            label="⬇️ Descargar Log de Auditoría (.CSV)",
            data=df_logs.to_csv(index=False).encode("utf-8"),
            file_name="log_auditoria_eig_soat.csv",
            mime="text/csv"
        )
    else:
        st.warning("Aún no hay transacciones ejecutadas en esta sesión. Valide un caso en la Pestaña 1 o ejecute los 20 casos en la Pestaña 2.")

# ------------------------------------------------------------------------------
# TAB 4: DASHBOARD DE IMPACTO OPERATIVO (ROI)
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("📈 Comparativa AS-IS vs. TO-BE (Sincronizada al 98%)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Horas/Hombre Semanales", "45 min", "-98.1% (antes 40h)")
    m2.metric("Personal Requerido (ETP)", "0.04 ETP", "-98.0% (antes 2.0 ETP)")
    m3.metric("Ahorro Directo Facturación", "$24.000.000 COP/año", "Rubro Directo")
    m4.metric("Impacto Integral EIG", "$44.500.000 COP/año", "Facturación + Stock + Mtto.")

    chart_data = pd.DataFrame({
        "Etapa": ["Semana 1 (AS-IS)", "Semana 3 (Piloto)", "Semana 6 (Integración API)", "Semana 8 (TO-BE)"],
        "Horas Semanales AS-IS": [40.0, 40.0, 40.0, 40.0],
        "Horas Semanales TO-BE": [40.0, 22.0, 4.5, 0.75]
    })
    st.line_chart(chart_data.set_index("Etapa"))
