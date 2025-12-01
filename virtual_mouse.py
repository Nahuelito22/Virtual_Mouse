import cv2
import mediapipe as mp
import pyautogui
import math

# --- CONFIGURACIÓN ---
# Desactiva la seguridad de esquinas de PyAutoGUI para evitar cierres accidentales
# (Úsalo con cuidado, ten siempre lista la tecla 'q' para salir)
pyautogui.FAILSAFE = False 

# Obtener tamaño de pantalla
SCREEN_W, SCREEN_H = pyautogui.size()

# Sensibilidad: Aumenta para moverte más rápido con menos movimiento de mano
MOVEMENT_SENSITIVITY = 4.0 

# --- INICIALIZACIÓN DE MEDIAPIPE ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1, 
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# --- VARIABLES DE ESTADO ---
last_hand_x, last_hand_y = None, None
click_gesture_active = False

def get_finger_status(landmarks):
    """
    Devuelve una lista [Pulgar, Índice, Medio, Anular, Meñique] 
    con True si el dedo está levantado y False si está bajado.
    """
    status = []
    
    # IDs de las puntas de los dedos
    tips = [4, 8, 12, 16, 20]
    # IDs de las articulaciones medias (PIPs) para comparar
    pips = [3, 6, 10, 14, 18] # El 3 es la IP del pulgar
    
    # Lógica para el Pulgar (es diferente porque se mueve lateralmente)
    # Asumimos mano derecha, si x de la punta < x de la IP, está "abierto" (hacia la izquierda)
    # Nota: Esto puede variar si la mano está invertida, pero funciona para gestos básicos.
    status.append(landmarks[tips[0]].x < landmarks[pips[0]].x)
    
    # Lógica para los otros 4 dedos (se mueven verticalmente)
    for i in range(1, 5):
        status.append(landmarks[tips[i]].y < landmarks[pips[i]].y)
        
    return status

def main():
    global last_hand_x, last_hand_y, click_gesture_active
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("¡Error Crítico!: No se pudo acceder a la cámara.")
        return

    print("--- MOUSE VIRTUAL POR GESTOS ---")
    print("1. Índice levantado: Mover cursor")
    print("2. Puño cerrado: Clic Izquierdo")
    print("3. V (Índice + Medio): Clic Derecho")
    print("4. Tres dedos (Índice+Medio+Anular): Doble Clic")
    print("PRESIONA 'q' PARA SALIR")

    while True:
        success, frame = cap.read()
        if not success:
            continue

        # Espejar la cámara para que sea intuitivo (como un espejo)
        frame = cv2.flip(frame, 1)
        frame_h, frame_w, _ = frame.shape
        
        # Convertir a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        current_action = "Esperando mano..."

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            landmarks = hand_landmarks.landmark
            fingers_up = get_finger_status(landmarks)

            # --- LÓGICA DE GESTOS ---

            # 1. GESTO DE MOVER (Solo Índice levantado)
            # A veces el pulgar puede interferir, así que somos flexibles con el pulgar.
            if fingers_up[1] and not fingers_up[2] and not fingers_up[3] and not fingers_up[4]:
                current_action = "Moviendo..."
                click_gesture_active = False 
                
                index_x = landmarks[8].x
                index_y = landmarks[8].y
                
                if last_hand_x is None:
                    last_hand_x, last_hand_y = index_x, index_y
                else:
                    delta_x = index_x - last_hand_x
                    delta_y = index_y - last_hand_y
                    
                    # Mover mouse
                    pyautogui.move(delta_x * frame_w * MOVEMENT_SENSITIVITY, 
                                   delta_y * frame_h * MOVEMENT_SENSITIVITY)
                    
                    last_hand_x, last_hand_y = index_x, index_y
            
            else:
                # Si no movemos, reseteamos la posición de referencia para evitar saltos
                last_hand_x, last_hand_y = None, None

                # 2. CLIC IZQUIERDO (Puño cerrado o solo pulgar)
                if not any(fingers_up[1:]): # Si índice, medio, anular y meñique están bajados
                    current_action = "CLIC IZQUIERDO"
                    if not click_gesture_active:
                        pyautogui.click()
                        click_gesture_active = True
                
                # 3. CLIC DERECHO (Gesto de Paz / Victoria)
                elif fingers_up[1] and fingers_up[2] and not fingers_up[3]:
                    current_action = "CLIC DERECHO"
                    if not click_gesture_active:
                        pyautogui.rightClick()
                        click_gesture_active = True
                
                # 4. DOBLE CLIC (Tres dedos)
                elif fingers_up[1] and fingers_up[2] and fingers_up[3] and not fingers_up[4]:
                    current_action = "DOBLE CLIC"
                    if not click_gesture_active:
                        pyautogui.doubleClick()
                        click_gesture_active = True
                
                else:
                    current_action = "Gesto no detectado"
                    click_gesture_active = False

        else:
            last_hand_x, last_hand_y = None, None

        # Interfaz visual
        cv2.putText(frame, current_action, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2, cv2.LINE_AA)
        
        cv2.imshow('Virtual Mouse AI', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()

if __name__ == "__main__":
    main()