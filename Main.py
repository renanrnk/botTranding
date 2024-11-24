# Painel de Controle
import MacdRSIAlts
import multiprocessing
import StopDinamico

def run_macd():
    MacdRSIAlts.run_bot()
    
def run_stop():
    StopDinamico.run_bot()

if __name__ == "__main__":
    # Sobe na memória
    macd_near_process = multiprocessing.Process(target=run_macd)
    stop_dinam_process = multiprocessing.Process(target=run_stop)

    # Inicializa
    macd_near_process.start()
    stop_dinam_process.start()

    # Sincroniza
    macd_near_process.join()
    stop_dinam_process.join()