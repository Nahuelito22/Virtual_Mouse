import cv2
import mediapipe as mp
import pyautogui

# --- CONFIGURACIÓN Y CONSTANTES ---
pyautogui.FAILSAFE = False
SCREEN_W, SCREEN_H = pyautogui.size()

# ¡NUEVO! Sensibilidad del movimiento. Aumenta para que el cursor se mueva más rápido.
# Un buen valor para empezar es entre 2 y 4.
MOVEMENT_SENSITIVITY = 3.0

# --- INICIALIZACIÓN DE LIBRERÍAS ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: No se puede abrir la cámara.")
    exit()

# --- VARIABLES DE ESTADO ---
# ¡NUEVO! Almacenan la última posición de la mano para el movimiento relativo.
last_hand_x, last_hand_y = None, None
click_gesture_active = False

# --- FUNCIONES AUXILIARES DE DETECCIÓN DE GESTOS ---

def get_finger_status(landmarks):
    """Devuelve una lista de booleanos indicando si cada dedo está levantado."""
    status = []
    finger_tip_ids = [
        mp_hands.HandLandmark.THUMB_TIP, mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    finger_pip_ids = [
        mp_hands.HandLandmark.THUMB_IP, mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP, mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP
    ]
    
    # Pulgar (eje X)
    status.append(landmarks[finger_tip_ids[0]].x < landmarks[finger_pip_ids[0]].x)
    # Otros 4 dedos (eje Y)
    for i in range(1, 5):
        status.append(landmarks[finger_tip_ids[i]].y < landmarks[finger_pip_ids[i]].y)
        
    return status

# --- BUCLE PRINCIPAL ---
print("Iniciando control por gestos v2.0.")
print("- Dedo índice levantado: Mover cursor (modo relativo)")
print("- Puño cerrado: Clic izquierdo")
print("- Gesto de victoria: Clic derecho")
print("- Índice, corazón y anular levantados: Doble clic")
print("Presiona 'q' para salir.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: continue

    frame = cv2.flip(frame, 1)
    frame_h, frame_w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    current_action = "Mano no detectada"

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = hand_landmarks.landmark
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Obtener el estado de los dedos (levantados o no)
        # [pulgar, indice, corazon, anular, meñique]
        fingers_up = get_finger_status(landmarks)

        # --- DETECCIÓN DE GESTOS Y ACCIONES ---
        
        # Gesto de Mover (solo índice levantado)
        if fingers_up == [False, True, False, False, False]:
            current_action = "Moviendo cursor..."
            click_gesture_active = False # Permitir futuros clics
            
            # --- LÓGICA DE MOVIMIENTO RELATIVO ---
            index_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            
            if last_hand_x is None: # Si es la primera vez que detectamos el gesto
                last_hand_x, last_hand_y = index_tip.x, index_tip.y
            else:
                # Calcular el cambio (delta) desde la última posición
                delta_x = index_tip.x - last_hand_x
                delta_y = index_tip.y - last_hand_y
                
                # Mover el ratón proporcionalmente al cambio y la sensibilidad
                pyautogui.move(delta_x * frame_w * MOVEMENT_SENSITIVITY, 
                               delta_y * frame_h * MOVEMENT_SENSITIVITY)
                
                # Actualizar la última posición
                last_hand_x, last_hand_y = index_tip.x, index_tip.y
        
        else:
            # Si no estamos en modo "mover", reiniciamos la última posición.
            # Esto es clave: permite "levantar" el ratón y reposicionar la mano.
            last_hand_x, last_hand_y = None, None

            # Gesto de Clic Izquierdo (Puño cerrado)
            if fingers_up == [False, False, False, False, False] or fingers_up == [True, False, False, False, False]:
                current_action = "CLIC IZQUIERDO"
                if not click_gesture_active:
                    pyautogui.click(button='left')
                    print("Clic Izquierdo")
                    click_gesture_active = True
            
            # Gesto de Clic Derecho (Victoria)
            elif fingers_up == [False, True, True, False, False]:
                current_action = "CLIC DERECHO"
                if not click_gesture_active:
                    pyautogui.click(button='right')
                    print("Clic Derecho")
                    click_gesture_active = True
            
            # ¡NUEVO! Gesto de Doble Clic (Índice, Corazón, Anular)
            elif fingers_up == [False, True, True, True, False]:
                current_action = "DOBLE CLIC"
                if not click_gesture_active:
                    pyautogui.doubleClick()
                    print("Doble Clic")
                    click_gesture_active = True
            else:
                # Cualquier otro gesto resetea la bandera de clic
                current_action = "Gesto no reconocido"
                click_gesture_active = False

    else:
        # Si no se detecta ninguna mano, reiniciar el estado del movimiento
        last_hand_x, last_hand_y = None, None
        
    cv2.putText(frame, current_action, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.imshow('Control por Gestos v2.0', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
hands.close()
print("Programa finalizado.")