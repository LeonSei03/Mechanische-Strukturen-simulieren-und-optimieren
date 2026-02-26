import streamlit as st 
from ui_logik import OptimierungsLogger

def init_session_state(): 
    '''
    Initialisiert alle benötigten st.session_state Keys mit den Default Werten 
    '''

    if "entwurf_kraefte" not in st.session_state:
        st.session_state.entwurf_kraefte = {} #Knoten_id : (fx, fz)

    if "entwurf_lager" not in st.session_state:
        st.session_state.entwurf_lager = {} #Knoten_id: lager_typ_string

    if "kraft_knoten_id" not in st.session_state:
        st.session_state.kraft_knoten_id = None

    if "lager_knoten_id" not in st.session_state:
        st.session_state.lager_knoten_id = None

    if "struktur" not in st.session_state:
        st.session_state.struktur = None

    if "u" not in st.session_state:
        st.session_state.u = None 

    if "mapping" not in st.session_state:
        st.session_state.mapping = None 

    if "historie" not in st.session_state:
        st.session_state.historie = None 

    if "ausgewaehlter_knoten_id" not in st.session_state:
        st.session_state.ausgewaehlter_knoten_id = None 

    if "last_knoten_id" not in st.session_state:
        st.session_state.last_knoten_id = None 

    if "start_masse" not in st.session_state: 
        st.session_state.start_masse = None 

    #states für neuen tab 
    if "struktur_ref" not in st.session_state:
        st.session_state.struktur_ref = None

    if "u_ref" not in st.session_state:
        st.session_state.u_ref = None

    if "mapping_ref" not in st.session_state:
        st.session_state.mapping_ref = None

    # sessionstates für optimierung
    if "optimierer" not in st.session_state:
        st.session_state.optimierer = None

    if "optimierung_laeuft" not in st.session_state:
        st.session_state.optimierung_laeuft = False

    if "stop_angefordert" not in st.session_state:
        st.session_state.stop_angefordert = False

    if "checkpoint_pfad" not in st.session_state:
        st.session_state.checkpoint_pfad = None

    #Damit die Flash-Messages angezeigt werden überall 
    if "flash" not in st.session_state:
        st.session_state.flash = [] #Liste für (type und text)

    # Sessionstates für die Video Animation
    if "gif_frames" not in st.session_state:
        st.session_state.gif_frames = []

    if "gif_recording" not in st.session_state:
        st.session_state.gif_recording = False

    # sessionstates für das Optimierungs-logging
    if "optimierungs_protokoll" not in st.session_state:
        st.session_state.optimierungs_protokoll = OptimierungsLogger()

    if "protokoll_zeilen_anzahl" not in st.session_state:
        st.session_state.protokoll_zeilen_anzahl = 250

    if "protokoll_ausfuehrlich" not in st.session_state:
        st.session_state.protokoll_ausfuehrlich = False

def flash(typ: str, text: str):
    #type sind success, info, warning und error 
    st.session_state.flash.append((typ, text))

def show_flash():
    if st.session_state.flash:
        for typ, text in st.session_state.flash:
            getattr(st, typ)(text)
        st.session_state.flash.clear()