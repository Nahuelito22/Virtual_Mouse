import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math

# --- CONFIGURACIÓN ---
pyautogui.FAILSAFE = False
wScr, hScr = pyautogui.size()
wCam, hCam = 640, 480
frameR = 100          # Zona de reducción (ROI)
smoothening = 5       # Suavizado

# Colores (B, G, R)
COLOR_MOUSE = (255, 0, 255)  # Violeta
COLOR_CLICK = (0, 255, 0)    # Verde
COLOR_PAUSE = (0, 0, 255)    # Rojo
COLOR_UI    = (255, 255, 255) # Blanco

# --- INICIALIZACIÓN ---
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

plocX, plocY = 0, 0
clocX, clocY = 0, 0
is_paused = False  # Estado inicial

def get_fingers_up(lm):
    """Devuelve qué dedos están levantados [Pulgar, Índice, Medio, Anular, Meñique]"""
    fingers = []
    tips = [4, 8, 12, 16, 20] # Puntas
    pips = [3, 6, 10, 14, 18] # Articulaciones medias (o base para pulgar)

    # Pulgar (eje X para mano derecha - lógica simplificada)
    # Nota: Esto asume mano derecha frente a cámara. 
    if lm[tips[0]].x < lm[pips[0]].x: 
        fingers.append(1)
    else:
        fingers.append(0)

    # Otros 4 dedos (eje Y - Arriba es menor valor en Y)
    for i in range(1, 5):
        if lm[tips[i]].y < lm[pips[i]].y:
            fingers.append(1)
        else:
            fingers.append(0)
    return fingers

def draw_ui(img, paused):
    """Dibuja el menú y estado en la pantalla"""
    # Fondo semitransparente arriba
    overlay = img.copy()
    cv2.rectangle(img, (0, 0), (wCam, 60), (0, 0, 0), cv2.FILLED)
    cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

    # Estado
    if paused:
        cv2.putText(img, "ESTADO: PAUSADO (Abre la mano)", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_PAUSE, 2)
    else:
        cv2.putText(img, "ESTADO: ACTIVO", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_CLICK, 2)

    # Instrucciones pequeñas abajo
    cv2.putText(img, "Indice: Mover | Pellizco: Click | Shaka: Salir", (10, hCam - 10), 
                cv2.FONT_HERSHEY_PLAIN, 1, COLOR_UI, 1)

def main():
    global plocX, plocY, clocX, clocY, is_paused
    
    while True:
        success, frame = cap.read()
        if not success: continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        # Dibujar UI siempre
        draw_ui(frame, is_paused)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            lm = hand_landmarks.landmark
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Obtener estado de dedos
            fingers = get_fingers_up(lm)
            
            # Coordenadas clave
            x1, y1 = int(lm[8].x * wCam), int(lm[8].y * hCam)   # Índice
            x2, y2 = int(lm[4].x * wCam), int(lm[4].y * hCam)   # Pulgar
            x_pinky, y_pinky = int(lm[20].x * wCam), int(lm[20].y * hCam) # Meñique
            x_mid, y_mid = int(lm[12].x * wCam), int(lm[12].y * hCam) # Medio

            # --- 1. GESTO DE SALIDA (SHAKA 🤙) ---
            # Distancia entre Pulgar (4) y Meñique (20) < 30 y los dedos del medio bajados
            dist_exit = math.hypot(x2 - x_pinky, y2 - y_pinky)
            if dist_exit < 40 and fingers[1] == 0 and fingers[2] == 0:
                print("Saliendo de la App...")
                break

            # --- 2. GESTIÓN DE PAUSA ---
            # Si todos los dedos están bajados (Puño) -> PAUSAR
            if all(f == 0 for f in fingers):
                is_paused = True
            
            # Si todos los dedos están levantados (Palma) -> ACTIVAR
            if all(f == 1 for f in fingers):
                is_paused = False

            # --- 3. LÓGICA DEL MOUSE (Solo si NO está en pausa) ---
            if not is_paused:
                # Dibujar ROI
                cv2.rectangle(frame, (frameR, frameR), (wCam - frameR, hCam - frameR),
                              COLOR_MOUSE, 2)

                # Mover Mouse
                x3 = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
                y3 = np.interp(y1, (frameR, hCam - frameR), (0, hScr))

                clocX = plocX + (x3 - plocX) / smoothening
                clocY = plocY + (y3 - plocY) / smoothening

                try:
                    pyautogui.moveTo(clocX, clocY)
                except:
                    pass
                plocX, plocY = clocX, clocY

                # Clic Izquierdo (Pulgar + Índice)
                if math.hypot(x2 - x1, y2 - y1) < 30:
                    cv2.circle(frame, (x1, y1), 10, COLOR_CLICK, cv2.FILLED)
                    pyautogui.click()

                # Clic Derecho (Pulgar + Medio)
                if math.hypot(x2 - x_mid, y2 - y_mid) < 30:
                    cv2.circle(frame, (x_mid, y_mid), 10, (0,0,255), cv2.FILLED)
                    pyautogui.rightClick()

        cv2.imshow("Virtual Mouse AI", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()