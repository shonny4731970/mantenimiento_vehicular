import streamlit as st
from supabase import create_client, Client
import requests

# Configuración de página
st.set_page_config(page_title="Mantenimiento Vehicular Familiar", page_icon="🚗", layout="wide")

# Conexión a Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Sistema de Login / Permisos por sesión
st.sidebar.title("🔐 Acceso de Usuario")
user_email = st.sidebar.text_input("Correo electrónico", placeholder="usuario@familia.com").strip().lower()
is_admin = st.sidebar.checkbox("Modo Administrador global")

st.title("🚗 Control y Mantenimiento Vehicular")

if not user_email:
    st.info("Por favor, ingresa tu correo electrónico en la barra lateral para continuar.")
    st.stop()

st.sidebar.success(f"Sesión activa: **{user_email}**")

# Pestañas principales
tab_vehiculos, tab_mantenimientos, tab_nuevo = st.tabs(["🚘 Vehículos", "🛠️ Historial de Mantenimiento", "➕ Registrar Vehículo"])

# --- Pestaña 1: Vehículos ---
with tab_vehiculos:
    st.header("Vehículos Registrados")
    res_vehiculos = supabase.table("vehiculos").select("*").execute()
    vehiculos = res_vehiculos.data

    if not vehiculos:
        st.write("No hay vehículos registrados aún.")
    else:
        for v in vehiculos:
            with st.expander(f"🚗 {v['modelo']} (Odómetro: {v['odometro']})", expanded=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if v.get("imagen_url"):
                        st.image(v["imagen_url"], use_container_width=True)
                    else:
                        st.write("🖼️ *Sin imagen disponible*")
                with col2:
                    st.write(f"**VIN:** {v.get('vin', 'N/A')}")
                    st.write(f"**Propietario:** `{v['propietario_email']}`")

                    # Consulta API de VIN
                    if v.get("vin") and st.button("🔍 Decodificar VIN", key=f"vin_{v['id']}"):
                        try:
                            api_res = requests.get(f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{v['vin']}?format=json").json()
                            results = api_res.get("Results", [{}])[0]
                            st.json({"Marca": results.get("Make"), "Modelo": results.get("Model"), "Año": results.get("ModelYear")})
                        except Exception as e:
                            st.error(f"Error al consultar la API de VIN: {e}")

                    # Permisos de edición (Solo el propietario o Admin)
                    can_edit = (v["propietario_email"] == user_email) or is_admin
                    if can_edit:
                        nuevo_odo = st.text_input("Actualizar Odómetro", value=v["odometro"], key=f"odo_{v['id']}")
                        if st.button("Guardar Odómetro", key=f"btn_odo_{v['id']}"):
                            supabase.table("vehiculos").update({"odometro": nuevo_odo}).eq("id", v["id"]).execute()
                            st.success("Odómetro actualizado")
                            st.rerun()

# --- Pestaña 2: Mantenimientos ---
with tab_mantenimientos:
    st.header("Historial y Tareas Pendientes")
    if vehiculos:
        vehiculo_sel = st.selectbox("Seleccionar Vehículo", options=vehiculos, format_func=lambda x: f"{x['modelo']} ({x['propietario_email']})")
        if vehiculo_sel:
            res_maint = supabase.table("mantenimientos").select("*").eq("vehiculo_id", vehiculo_sel["id"]).execute()
            mantenimientos = res_maint.data

            can_edit_maint = (vehiculo_sel["propietario_email"] == user_email) or is_admin

            st.subheader(f"Mantenimientos para: {vehiculo_sel['modelo']}")
            if mantenimientos:
                for m in mantenimientos:
                    col1, col2, col3 = st.columns([1, 3, 2])
                    col1.write(f"{m.get('icono', '🛠️')} **{m['tarea']}**")
                    col2.write(f"Detalle: {m.get('detalle', 'N/A')} | Estado: `{m['estado']}`")
                    with col3:
                        if can_edit_maint and m['estado'] == "Pendiente":
                            if st.button("Marcar Completado", key=f"done_{m['id']}"):
                                supabase.table("mantenimientos").update({"estado": "Completado"}).eq("id", m["id"]).execute()
                                st.rerun()
            else:
                st.info("No hay tareas registradas para este vehículo.")

            if can_edit_maint:
                st.markdown("---")
                st.subheader("➕ Agregar Tarea de Mantenimiento")
                with st.form(key=f"form_maint_{vehiculo_sel['id']}"):
                    tarea = st.text_input("Tarea (ej: Cambio de aceite)")
                    icono = st.selectbox("Icono", ["🛠️", "🛞", "🔋", "🛢️", "🛑"])
                    detalle = st.text_area("Detalles / Notas")
                    sub_m = st.form_submit_button("Registrar Tarea")
                    if sub_m and tarea:
                        supabase.table("mantenimientos").insert({
                            "vehiculo_id": vehiculo_sel["id"],
                            "tarea": tarea,
                            "icono": icono,
                            "detalle": detalle,
                            "estado": "Pendiente"
                        }).execute()
                        st.success("Tarea añadida exitosamente")
                        st.rerun()

# --- Pestaña 3: Registrar Vehículo ---
with tab_nuevo:
    st.header("Registrar Nuevo Vehículo")
    with st.form("form_nuevo_vehiculo"):
        modelo = st.text_input("Modelo del Vehículo (ej: Toyota Corolla 2020)")
        odometro = st.text_input("Odómetro Inicial (ej: 45,000 km)")
        vin = st.text_input("Número VIN (Opcional)")
        imagen_url = st.text_input("URL de Imagen del Vehículo (Opcional)")
        propietario = st.text_input("Correo del Propietario", value=user_email)
        submit = st.form_submit_button("Guardar Vehículo")

        if submit and modelo and odometro and propietario:
            supabase.table("vehiculos").insert({
                "modelo": modelo,
                "odometro": odometro,
                "vin": vin,
                "imagen_url": imagen_url,
                "propietario_email": propietario
            }).execute()
            st.success("Vehículo registrado correctamente")
            st.rerun()
