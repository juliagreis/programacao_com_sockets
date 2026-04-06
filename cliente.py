import socket
import time
import threading

HOSTP2P='0.0.0.0'
HOST_SERVIDOR_CENTRAL='200.235.131.66'
PORTA_SERVIDOR_CENTRAL=10000

meu_nome_usuario="" 
peer_ativo= None

def pegar_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def KEEP(servidor_central_socket):
    "Função que envia 'KEEP' a cada 5 segundo para o servidor central em segundo plano"
    while True:
        try:
            time.sleep(5) #em segundos
            servidor_central_socket.send("KEEP\r\n".encode('utf-8'))
        except Exception as e:
            print("Erro de conexão: ", e)
            return
            
def menu(servidor_central_socket):
    global peer_ativo
    "Menu de interacao para digitiar os comandos list, chat e exit"
    print("----------------CHAT P2P ----------------")
    print("Comandos: /list, /chat <nome>, /exit")

    while True:
        cmd=input()

        if cmd=="/list": #listar todos os usuarios
            servidor_central_socket.send("LIST\r\n".encode('utf-8'))

        elif cmd=="/exit":
            print("Encerrando conexão do cliente")
            if peer_ativo:
                peer_ativo.close()
            servidor_central_socket.close()
            break
        elif cmd.startswith("/chat"): 
            partes=cmd.split()
            if len(partes)==2: 
                nome_destino=partes[1]
                comando_ADDR=f"ADDR {nome_destino}\r\n"
                servidor_central_socket.send(comando_ADDR.encode('utf-8'))
                print(f"Solicitando IP e Porta do usuário {nome_destino} ao servidor")
            else:
                print("Erro: formato correto: /chat <nome_do_usuario>")
        else: #não é comando nenhum, entao é mensagem para o chat
            if peer_ativo is not None: #se tem conexao estabelecida com algum peer
                try:
                    # Envia a mensagem comum com \r\n
                    msg_chat = f"{cmd}\r\n"
                    peer_ativo.send(msg_chat.encode('utf-8'))
                except Exception as e:
                    print("Erro ao enviar mensagem. A conexão pode ter caído.")
                    peer_ativo = None
            else:
                print("Erro: Nenhuma conexão P2P ativa. Use /chat <nome> primeiro.")


def LISTEN(p2p_socket):
    """coloca o socket para escutar conexões"""
    #p2p_socket.listen()
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

            msg = msg.decode('utf-8').split('\r\n') # decodifica os bytes para string
            for m in msg:
                if not m:
                    continue
                    
                # Se for o comando USER de um novo peer se conectando
                if m.startswith("USER "):
                    nome_peer = m.split(" ")[1]
                    print(f"\n{nome_peer} conectou-se a você!")

                    global peer_ativo
                    peer_ativo = conn
                else:
                    # Imprime a mensagem normal do chat
                    print(f"[{addr}] {m}")
    
    except Exception as e:
        print("Erro com peer:", e)

    finally:
        conn.close()

def LISTEN_SERVIDOR(sock):
    global peer_ativo
    global meu_nome_usuario

    while True:
        try:
            resposta = sock.recv(1024)

            if not resposta:
                print("Servidor desconectado.")
                break

            #Recebi uma mensagem
            mensagens=resposta.decode('utf-8').split('\r\n')
            #para nao considerar algum caso de linha vazia
            for msg in mensagens:
                if not msg:
                    continue
            
                #se a mensagem enviada por um endereço, conectamos
                if msg.startswith("ADDR"):
                    partes = msg.split(':')
                    if len(partes) >= 3:
                        ip_peer = pegar_ip_local()  # ignora o IP do servidor, usa o local
                        porta_peer = int(partes[2].strip())
                        try:
                            #criando socket p2p 
                            novo_peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            novo_peer_sock.connect((ip_peer, porta_peer))
                            print("estou tentando")
                            #salva qual peer esta ativo
                            peer_ativo=novo_peer_sock

                            #enviar somando user para se indentificar ao peer
                            cmd=f"USER {meu_nome_usuario}\r\n"
                            novo_peer_sock.send(cmd.encode("utf-8"))

                            #cria um nova thread para escutar tudo que esse peer em especifico enviar
                            #permitindo manter conexao com mais de um peer simultaneamente
                            thread_peer=threading.Thread(target=handle_peer,args=(novo_peer_sock,(ip_peer,porta_peer)))
                            thread_peer.daemon = True
                            thread_peer.start()
                            print("Conexão P2P estabelecida com sucesso!")
                        except Exception as e:
                            print(f"\n[Erro] Não foi possível conectar ao peer: {e}")
                else: #se for apenas outra mensagem do servidor, só imprime
                    print("Servidor:", resposta.decode('utf-8'))

        except Exception as e:
            print("Erro ao receber do servidor:", e)
            break

def main():
    global meu_nome_usuario
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
    meu_nome_usuario=nomeUsuario

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
    threadKEEP.daemon=True
    threadKEEP.start()
    
    #3.2 O socket P2P deve ficar escutando conexões de outros clientes
    #Como outros peers podem tentar se conectar a qualquer momento,
    #é necessário manter o socket em modo de escuta contínua (listen + accept),
    #Para não bloquear o restante da aplicação uma thread
    #fica constantemente aguardando novas conexões de peers.
    p2p_socket.listen()
    print(f"escutando na porta {myPORTA}")
    thread_listen = threading.Thread(target=LISTEN, args=(p2p_socket,))
    thread_listen.daemon = True  # encerra junto com o programa
    thread_listen.start()

    #3.3 Thread para escutar mensagens do servidor central
    #Como o servidor pode enviar respostas a qualquer momento (ex: LIST, ADDR, etc.),
    #é necessário manter o cliente constantemente ouvindo o socket conectado ao servidor.
    #Para evitar bloquear a interação do usuário (menu),
    #uma thread separada fica responsável por receber (recv) e exibir
    #as mensagens enviadas pelo servidor central em tempo real.
    thread_server = threading.Thread(target=LISTEN_SERVIDOR, args=(servidor_central_socket,))
    thread_server.daemon = True
    thread_server.start()

    menu(servidor_central_socket)
    return


if __name__ == "__main__":
    main()