import GerenciamentoRisco as gr
import config as k
import time
import schedule

def run_bot():
    def job():
        gr.stop_dinamico(take_profit=0.035, stop_loss = 0.006)
    
    schedule.every(25).seconds.do(job)

    while True:
        try:
            schedule.run_pending()
        except:
            print('Problemas de conexão...')
            time.sleep(10)

if __name__ == "__main__":  
    run_bot()