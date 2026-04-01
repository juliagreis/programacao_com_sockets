import socket
import time
import threading

HOSTP2P='0.0.0.0'
HOST_SERVIDOR_CENTRAL='200.235.131.66'
PORTA_SERVIDOR_CENTRAL=10000

def KEEP(servidor_central_socket):
    "Função que envia 'KEEP' a cada 5 segundo para o servidor central em segundo plano"
    while True:
        try:
            time.sleep(5) #em segundos
            servidor_central_socket.send("KEEP\r\n",encode('utf-8'))
        except Exception as e:
            print("Erro de conexão: ", e)
            return

def main():

    #-------- 1. INICIALIZAÇÃO DO CLIENTE---------
    print("Iniciando cliente...")

    #Criar socket TCP
    p2p_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #Faz o bind na porta 0, deixando para o SO escolher uma porta livre
    p2p_socket.bind((HOSTP2P,0))
    #Descobre qual IP e PORTA o SO atribuiu: retorno (ip,porta)
    myIP,myPORTA=p2p_socket=p2p_socket.getsockname()

    print(f"Cliente IP:{myIP} pronto para estabelecer conexões P2P na porta {myPORTA}.")

    #Pedir nome de usuário (não pode conter ':')
    nomeUsuario=int(input ("Digite seu nome de usuário: "))

    #---------2. Conectar no servidor central--------
    #Cria um socket exclusivamente para falar com o servidor central
    servidor_central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        #Tenta estabelecer a conexão TCP
        servidor_central_socket.connect((HOST_SERVIDOR_CENTRAL, PORTA_SERVIDOR_CENTRAL))
        print("-- Conectado ao servidor central! --")

        #Monta mensagem de registro -> função USER
        msg_registro = f"USER {nomeUsuario}:{myPORTA}\r\n" #\r\n especificado no PDF

        #Enviar registro ao servidor central
            #obs: o socket trasmite bytes, por isso deve-se usar o .encode()
        servidor_central_socket.send(msg_registro.encode('utf-8'))
        print(f"-- Registro enviado ao servidor central: {msg_registro}")

    except Exception as e:
        print("Erro ao conectar ao servidor central: ",e)
        return

    #-------- 3. Iniciar as Threads (para o KEEP, para escutar peers, etc.)--------

    #3.1 Comando KEEP deve ser enviado a cada 5s para o servidor não apagar o registro
    #Como esse envio deve acontecer de maneira constante e em segundo plano,
    #permitindo que eu continue enviando mensagens, designo uma thread para a função, que contem
    #um while true, mantendo a thread presa dentro da função
    threadKEEP= threading.Thread(target=KEEP, args = (servidor_central_socket,)).start()
    input("Cliente rodando! Pressione ENTER para sair do programa...\n") #só pra testar

if __name__ == "__main__":
    main()