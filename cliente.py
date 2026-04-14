"""
Código feito por JÚLIA GOMES REIS 116209 e AYLLA KATRINE SOUZA MENDES 116214

Esse código é um cliente de chat P2P onde você primeiro digita um nome de usuário e se conecta a um servidor central. 
Depois disso, você usa comandos no terminal: “/list” mostra quem está disponível, “/chat <nome>” inicia uma conexão direta com outro usuário, “/peers” mostra com quem você 
já está conectado, “/switch <nome>” alterna entre conversas ativas, “/bye” encerra a conversa atual e “/exit” fecha tudo. As funções principais trabalham em paralelo com 
threads: KEEP mantém seu registro ativo no servidor enviando mensagens periódicas, LISTEN aceita conexões de outros usuários, LISTEN_SERVIDOR recebe respostas do servidor 
(como IP e porta de outros peers), e handle_peer cuida da troca de mensagens com cada pessoa conectada. O programa permite conversar com várias pessoas ao mesmo tempo 
mantendo várias conexões abertas, mas você envia mensagens apenas para um “peer ativo” por vez, podendo alternar entre eles sem precisar reconectar.
"""

import socket
import time
import threading

HOSTP2P='0.0.0.0'
HOST_SERVIDOR_CENTRAL='200.235.131.66'
PORTA_SERVIDOR_CENTRAL=10000

meu_nome_usuario="" 
peer_ativo= None
peers_conectados = {}    #nome_peer: socket

#Lock para evitar condições de corrida entre as threads
lock_peer_ativo = threading.Lock()  # socket do peer atual
lock_peers_conectados = threading.Lock() # protege peers_conectados

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
    "Menu de interacao para digitiar os comandos list, chat e exit\n/peers para ver todos os usuários que você está conectado\n/switch para enviar mensagens para outro peer conectado"

    print("----------------CHAT P2P ----------------")
    print("Comandos: /list, /chat <nome>, /peers, /switch <nome>, /bye, /exit")

    while True:
        cmd=input()

        if cmd=="/list": #listar todos os usuarios
            servidor_central_socket.send("LIST\r\n".encode('utf-8'))

        elif cmd == "/exit":
            print("Encerrando...")
            with lock_peers_conectados:
                for sock in list(peers_conectados.values()):
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                        sock.close()
                    except Exception:
                        pass
                peers_conectados.clear()
            with lock_peer_ativo:
                peer_ativo = None
            try:
                servidor_central_socket.shutdown(socket.SHUT_RDWR)
                servidor_central_socket.close()
            except Exception:
                pass
            break

        elif cmd == "/peers":
            #lista todos os peers com conexão P2P estabelecida
            with lock_peers_conectados:
                nomes = list(peers_conectados.items())
            with lock_peer_ativo:
                ativo_sock = peer_ativo
 
            if not nomes:
                print("Nenhum peer conectado no momento.")
            else:
                print("Peers conectados:")
                for nome, sock in nomes:
                    print(f"  {nome}")

        elif cmd.startswith("/switch "):
            # Troca o peer ativo sem encerrar as outras conexões
            nome_alvo = cmd.split(" ", 1)[1].strip()
            with lock_peers_conectados:
                sock_alvo = peers_conectados.get(nome_alvo)
            if sock_alvo:
                with lock_peer_ativo:
                    peer_ativo = sock_alvo
                print(f"Peer ativo: {nome_alvo}")
            else:
                print(f"Peer '{nome_alvo}' nao encontrado. Use /peers.")

        elif cmd.startswith("/chat"): 
            partes=cmd.split()
            if len(partes)==2: 
                nome_destino=partes[1]

                # Se já há conexão local com esse peer, apenas troca o ativo
                with lock_peers_conectados:
                    ja_conectado = nome_destino in peers_conectados
                    sock_alvo = peers_conectados.get(nome_destino)
                    
                if ja_conectado:
                    with lock_peer_ativo:
                        peer_ativo = sock_alvo
                    print(f"Você já está conectado a {nome_destino}. Peer ativo alterado.")
                else:
                    # Solicita endereço ao servidor para abrir nova conexão P2P
                    comando_ADDR=f"ADDR {nome_destino}\r\n"
                    servidor_central_socket.send(comando_ADDR.encode('utf-8'))
                    print(f"Solicitando IP e Porta do usuário {nome_destino} ao serv    idor")
            else:
                print("Erro: formato correto: /chat <nome_do_usuario>")
                
        elif cmd == "/bye":
            #Encerra apenas a conexão com o peer atualmente ativo
            with lock_peer_ativo:
                sock_para_fechar = peer_ativo
                peer_ativo = None
 
            if sock_para_fechar:
                with lock_peers_conectados:
                    nome_removido = None
                    for nome, sock in list(peers_conectados.items()):
                        if sock is sock_para_fechar:
                            nome_removido = nome
                            break
                    if nome_removido:
                        del peers_conectados[nome_removido]

                    if peers_conectados:
                        novo_sock = next(iter(peers_conectados.values()))
                        with lock_peer_ativo:
                            peer_ativo = novo_sock
                    else:
                        with lock_peer_ativo:
                            peer_ativo = None

                try:
                    sock_para_fechar.shutdown(socket.SHUT_RDWR)
                    sock_para_fechar.close()
                except Exception:
                    pass
                print("Conexão P2P encerrada.")
            else:
                print("Nenhuma conexão P2P ativa.")

        else: #não é comando nenhum, entao é mensagem para o chat
            with lock_peer_ativo:
                sock_atual = peer_ativo
            if sock_atual is not None:
                try:
                    msg_chat = f"{cmd}\r\n"
                    sock_atual.send(msg_chat.encode('utf-8'))
                except Exception:
                    print("Erro ao enviar mensagem. A conexão pode ter caído.")
                    with lock_peer_ativo:
                        if peer_ativo is sock_atual:
                            peer_ativo = None
            else:
                print("Nenhuma conexão P2P ativa. Use /chat <nome> primeiro.")

def LISTEN(p2p_socket):
    """coloca o socket para escutar conexões"""
    #p2p_socket.listen()
    print("Aguardando conexões P2P...")

    while True:
        try:
            conn, addr = p2p_socket.accept()
            print(f"Conexão recebida de {addr}")

            # cria uma thread para lidar com esse peer
            thread = threading.Thread(target=handle_peer, args=(conn, addr, None))
            thread.daemon = True
            thread.start()

        except Exception as e:
            print("Erro ao aceitar conexão:", e)
            break

def handle_peer(conn, addr,nome_conhecido):
    global peer_ativo
    nome_peer = nome_conhecido

    # Se ja sabemos o nome (iniciamos a conexao), registra agora
    if nome_peer is not None:
        with lock_peers_conectados:
            peers_conectados[nome_peer] = conn
        with lock_peer_ativo:
            peer_ativo = conn
        print(f"Conexao P2P estabelecida com {nome_peer}!")

    try:
        while True:
            msg = conn.recv(1024)  #recebe dados do peer até 1024 bytes

            if not msg:
                print(f"Conexão encerrada por {addr}") #encerra a conexão se não houver msg
                break

            msg = msg.decode('utf-8').split('\r\n') #decodifica os bytes para string
            for m in msg:
                if not m:
                    continue
                    
                # Se for o comando USER de um novo peer se conectando
                if m.startswith("USER "):
                    nome_peer = m.split(" ")[1]
                    print(f"\n{nome_peer} conectou-se a você!")
                    
                    with lock_peers_conectados:
                        peers_conectados[nome_peer] = conn
                    with lock_peer_ativo:
                        peer_ativo = conn
                else:
                    # Imprime a mensagem normal do chat
                    print(f"[{nome_peer}] {m}")
    except OSError:
        pass
    except Exception as e:
        print("Erro com peer:", e)

    finally:
        with lock_peers_conectados:
            if nome_peer and peers_conectados.get(nome_peer) is conn:
                del peers_conectados[nome_peer]
        with lock_peer_ativo:
            if peer_ativo is conn:
                peer_ativo = None
        try:
            conn.close()
        except Exception:
            pass        

def LISTEN_SERVIDOR(sock):
    global peer_ativo

    while True:
        try:
            resposta = sock.recv(1024)

            if not resposta:
                print("Servidor desconectado.")
                break

            mensagens=resposta.decode('utf-8').split('\r\n')

            for msg in mensagens:
                if not msg:
                    continue
            
                if msg.startswith("ADDR"):
                    conteudo = msg[5:]
                    partes = conteudo.split(':')

                    if len(partes) >= 3:
                        nome_peer  = partes[0].strip()
                        ip_peer=partes[1].strip()
                        porta_peer = int(partes[2].strip())
                        try:
                            novo_peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            novo_peer_sock.connect((ip_peer, porta_peer))

                            with lock_peer_ativo:
                                peer_ativo=novo_peer_sock

                            cmd=f"USER {meu_nome_usuario}\r\n"
                            novo_peer_sock.send(cmd.encode("utf-8"))

                            thread_peer=threading.Thread(target=handle_peer,args=(novo_peer_sock,(ip_peer,porta_peer),  nome_peer))
                            thread_peer.daemon = True
                            thread_peer.start()

                        except Exception as e:
                            print(f"\n[Erro] Não foi possível conectar ao peer: {e}")
                else:
                    print("Servidor:", msg)

        except Exception as e:
            #print("Erro ao receber do servidor:", e)
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

    #print(f"Cliente IP:{myIP} pronto para estabelecer conexões P2P na porta {myPORTA}.")

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
    thread_listen.daemon = True
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