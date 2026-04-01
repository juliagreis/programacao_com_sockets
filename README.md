# programacao_com_sockets
Trabalho 1 da disciplina de Redes de computadores da UFV

# Ideia do programa:

Em vez de criar um sistema cliente-servidor tradicional, onde todas as mensagens de texto passam por um servidor central, a ideia é construir uma rede P2P. Ou seja, o papel do servidor central é fornecer informação sobre o estado dos usuários da rede e como estabelecer uma conexão com eles. Dessa forma, quando um usuário deseja se conectar com outro, ele deve pedir ao servidor central qual é o endereço de IP e a porta daquele usuário pelo comando ADDR <nome>. Nesse momento, o contato com o servidor é matido apenas para manter o status do usuário, mas é o programa do cliente que estabelece uma conexão TCP direta com o peer escolhido.