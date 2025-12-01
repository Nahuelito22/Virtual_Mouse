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

# Colores (B, G, R) - Código de colores para saber qué haces
COLOR_MOUSE  = (255, 0, 255)   # Violeta
COLOR_LEFT   = (0, 255, 0)     # Verde (Clic Izquierdo)
COLOR_DOUBLE = (255, 165, 0)   # Cian/Celeste (Doble Clic)
COLOR_RIGHT  = (0, 0, 255)     # Rojo (Clic Derecho)
COLOR_EXIT   = (0, 255, 255)   # Amarillo (Salir)
COLOR_UI     = (255, 255, 255) # Blanco

# --- INICIALIZACIÓN ---
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

plocX, plocY = 0, 0
clocX, clocY = 0, 0
is_paused = False 

def get_fingers_up(lm):
    """Detecta qué dedos están levantados"""
    fingers = []
    tips = [4, 8, 12, 16, 20] 
    pips = [3, 6, 10, 14, 18] 

    # Pulgar
    if lm[tips[0]].x < lm[pips[0]].x: 
        fingers.append(1)
    else:
        fingers.append(0)

    # Índice, Medio, Anular, Meñique
    for i in range(1, 5):
        if lm[tips[i]].y < lm[pips[i]].y:
            fingers.append(1)
        else:
            fingers.append(0)
    return fingers

def draw_ui(img, paused):
    overlay = img.copy()
    cv2.rectangle(img, (0, 0), (wCam, 80), (0, 0, 0), cv2.FILLED)
    cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

    if paused:
        cv2.putText(img, "PAUSADO (Abre la mano)", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(img, "ACTIVO (Puno = Pausa)", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Leyenda de controles
    cv2.putText(img, "Indice: Izq | Medio: Doble | Anular: Der | Menique: Salir", (10, hCam - 10), 
                cv2.FONT_HERSHEY_PLAIN, 1, COLOR_UI, 1)

def main():
    global plocX, plocY, clocX, clocY, is_paused
    
    while True:
        success, frame = cap.read()
        if not success: continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        draw_ui(frame, is_paused)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            lm = hand_landmarks.landmark
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            fingers = get_fingers_up(lm)
            
            # Coordenadas de las PUNTAS de los dedos
            # 4=Pulgar, 8=Índice, 12=Medio, 16=Anular, 20=Meñique
            x_thumb, y_thumb = int(lm[4].x * wCam), int(lm[4].y * hCam)
            x_index, y_index = int(lm[8].x * wCam), int(lm[8].y * hCam)
            x_mid, y_mid     = int(lm[12].x * wCam), int(lm[12].y * hCam)
            x_ring, y_ring   = int(lm[16].x * wCam), int(lm[16].y * hCam)
            x_pinky, y_pinky = int(lm[20].x * wCam), int(lm[20].y * hCam)

            # --- 1. GESTIÓN DE PAUSA (Puño) ---
            if all(f == 0 for f in fingers):
                is_paused = True
            if all(f == 1 for f in fingers):
                is_paused = False

            # Si está pausado, no hacemos nada más
            if is_paused:
                cv2.imshow("Virtual Mouse AI", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
                continue

            # --- 2. GESTO DE SALIDA (Meñique + Pulgar) ---
            if math.hypot(x_thumb - x_pinky, y_thumb - y_pinky) < 30:
                cv2.line(frame, (x_thumb, y_thumb), (x_pinky, y_pinky), COLOR_EXIT, 3)
                cv2.putText(frame, "CERRANDO...", (wCam//2 - 100, hCam//2), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_EXIT, 3)
                cv2.imshow("Virtual Mouse AI", frame)
                cv2.waitKey(500)
                break

            # --- 3. MOVIMIENTO (Índice levantado) ---
            # Solo movemos si el índice está arriba.
            # Convertimos coordenadas
            x_mouse = np.interp(x_index, (frameR, wCam - frameR), (0, wScr))
            y_mouse = np.interp(y_index, (frameR, hCam - frameR), (0, hScr))

            # Suavizado
            clocX = plocX + (x_mouse - plocX) / smoothening
            clocY = plocY + (y_mouse - plocY) / smoothening
            
            # Dibujar caja ROI
            cv2.rectangle(frame, (frameR, frameR), (wCam - frameR, hCam - frameR), COLOR_MOUSE, 2)

            try:
                pyautogui.moveTo(clocX, clocY)
            except:
                pass
            plocX, plocY = clocX, clocY

            # --- 4. CLICS (Detección de pellizcos) ---
            
            # A) CLIC IZQUIERDO (Pulgar + Índice)
            dist_left = math.hypot(x_thumb - x_index, y_thumb - y_index)
            if dist_left < 30:
                cv2.circle(frame, (x_index, y_index), 10, COLOR_LEFT, cv2.FILLED)
                pyautogui.click()
                print("Clic Izquierdo")

            # B) DOBLE CLIC (Pulgar + Medio) - TU NUEVA IDEA
            dist_double = math.hypot(x_thumb - x_mid, y_thumb - y_mid)
            if dist_double < 30:
                cv2.circle(frame, (x_mid, y_mid), 10, COLOR_DOUBLE, cv2.FILLED)
                # Dibujamos línea para que se vea claro el gesto
                cv2.line(frame, (x_thumb, y_thumb), (x_mid, y_mid), COLOR_DOUBLE, 2)
                pyautogui.doubleClick()
                print("Doble Clic")
                pyautogui.sleep(0.2) # Pequeña espera para no hacer 50 doble clics seguidos

            # C) CLIC DERECHO (Pulgar + Anular)
            dist_right = math.hypot(x_thumb - x_ring, y_thumb - y_ring)
            if dist_right < 30:
                cv2.circle(frame, (x_ring, y_ring), 10, COLOR_RIGHT, cv2.FILLED)
                cv2.line(frame, (x_thumb, y_thumb), (x_ring, y_ring), COLOR_RIGHT, 2)
                pyautogui.rightClick()
                print("Clic Derecho")
                pyautogui.sleep(0.2) 

        cv2.imshow("Virtual Mouse AI", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()