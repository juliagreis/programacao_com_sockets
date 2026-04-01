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
            servidor_central_socket.send("KEEP\r\n".encode('utf-8'))
        except Exception as e:
            print("Erro de conexão: ", e)
            return

def LISTEN(p2p_socket):
    # coloca o socket para escutar conexões
    p2p_socket.listen()
    print("Aguardando conexões P2P...")

    while True:
        try:
            conn, addr = p2p_socket.accept()
            print(f"Conexão recebida de {addr}")

            # cria uma thread para lidar com esse peer
            thread = threading.Thread(target=handle_peer, args=(conn, addr))
            thread.start()

        except Exception as e:
            print("Erro ao aceitar conexão:", e)
            break

def handle_peer(conn, addr):
    try:
        while True:
            msg = conn.recv(1024)  # recebe dados do peer até 1024 bytes

            if not msg:
                print(f"Conexão encerrada por {addr}") # encerra a conexão se não houver msg
                break

            msg = msg.decode('utf-8') # decodifica os bytes para string
            print(f"[{addr}] {msg}")

    except Exception as e:
        print("Erro com peer:", e)

    finally:
        conn.close()

def main():

    #-------- 1. INICIALIZAÇÃO DO CLIENTE---------
    print("Iniciando cliente...")

    #Criar socket TCP
    p2p_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    #Faz o bind na porta 0, deixando para o SO escolher uma porta livre
    p2p_socket.bind((HOSTP2P,0))

    #Descobre qual IP e PORTA o SO atribuiu: retorno (ip,porta)
    myIP,myPORTA=p2p_socket.getsockname()

    print(f"Cliente IP:{myIP} pronto para estabelecer conexões P2P na porta {myPORTA}.")

    #Pedir nome de usuário (não pode conter ':')
    nomeUsuario=(input ("Digite seu nome de usuário: "))

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
    threadKEEP= threading.Thread(target=KEEP, args = (servidor_central_socket,))
    threadKEEP.start()
    
    #3.2 O socket P2P deve ficar escutando conexões de outros clientes
    #Como outros peers podem tentar se conectar a qualquer momento,
    #é necessário manter o socket em modo de escuta contínua (listen + accept),
    #Para não bloquear o restante da aplicação uma thread
    #fica constantemente aguardando novas conexões de peers.
    thread_listen = threading.Thread(target=LISTEN, args=(p2p_socket,))
    thread_listen.daemon = True  # encerra junto com o programa
    thread_listen.start()

    input("Cliente rodando! Pressione ENTER para sair do programa...\n") #só pra testar


if __name__ == "__main__":
    main()