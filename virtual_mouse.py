import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math

# --- CONFIGURACIÓN ---
pyautogui.FAILSAFE = False 
wScr, hScr = pyautogui.size()     
wCam, hCam = 640, 480             

# 1. AJUSTE DE ZONA (ROI)
# Mueve la mano dentro de este cuadro violeta para alcanzar toda la pantalla.
frameR = 100 

# 2. SUAVIZADO
# Lo bajé a 5. Si sigue sintiéndose "lento", prueba con 3.
smoothening = 5

# --- INICIALIZACIÓN ---
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# Variables para suavizado
plocX, plocY = 0, 0 
clocX, clocY = 0, 0 

def main():
    global plocX, plocY, clocX, clocY
    
    print("--- MOUSE PRO V4.0 ---")
    print("Índice: Mover cursor")
    print("Pellizco Índice + Pulgar: CLIC IZQUIERDO")
    print("Pellizco Medio + Pulgar: CLIC DERECHO")
    print("Presiona 'q' para salir.")

    while True:
        success, frame = cap.read()
        if not success: continue

        # Espejar y procesar
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        # Dibujar cuadro ROI
        cv2.rectangle(frame, (frameR, frameR), (wCam - frameR, hCam - frameR),
                      (255, 0, 255), 2)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            lm = hand_landmarks.landmark
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # --- OBTENER COORDENADAS ---
            # Pulgar (4), Índice (8), Medio (12)
            x1, y1 = int(lm[8].x * wCam), int(lm[8].y * hCam)   # Índice
            x2, y2 = int(lm[4].x * wCam), int(lm[4].y * hCam)   # Pulgar
            x3, y3 = int(lm[12].x * wCam), int(lm[12].y * hCam) # Medio

            # --- 1. MOVIMIENTO (Con el Índice) ---
            # Solo movemos si NO estamos haciendo clic derecho (para evitar conflictos)
            
            # Convertir coordenadas (ROI)
            x3_interp = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
            y3_interp = np.interp(y1, (frameR, hCam - frameR), (0, hScr))

            # Suavizado
            clocX = plocX + (x3_interp - plocX) / smoothening
            clocY = plocY + (y3_interp - plocY) / smoothening

            try:
                pyautogui.moveTo(clocX, clocY)
            except:
                pass # Evitar errores en bordes de pantalla

            plocX, plocY = clocX, clocY

            # --- 2. CLIC IZQUIERDO (Índice + Pulgar) ---
            length_left = math.hypot(x2 - x1, y2 - y1)
            if length_left < 30:
                cv2.circle(frame, (x1, y1), 10, (0, 255, 0), cv2.FILLED) # Verde
                pyautogui.click()
                print("Clic Izquierdo")

            # --- 3. CLIC DERECHO (Medio + Pulgar) ---
            length_right = math.hypot(x2 - x3, y2 - y3)
            # Dibujamos línea visual para el dedo medio también
            cv2.line(frame, (x3, y3), (x2, y2), (255, 255, 0), 2) 

            if length_right < 30:
                cv2.circle(frame, (x3, y3), 10, (0, 0, 255), cv2.FILLED) # Rojo
                pyautogui.rightClick()
                print("Clic Derecho")

        cv2.imshow("Mouse AI Control", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()