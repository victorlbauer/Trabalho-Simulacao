# -*- coding: utf-8 -*-
import math
import random
import simpy

class StatisticsCollector():
    def __init__(self):
        self.data_t = 0.0
        self.data_w = 0.0
        self.data_x = 0.0
        self.data_nq = 0.0
        self.total_data_packets = 0.0
        
        self.voice_t = 0.0
        self.voice_w = 0.0
        self.voice_nq = 0.0
        self.total_voice_packets = 0.0
    
    def T_Data(self):
        return self.data_t/self.total_data_packets
    
    def W_Data(self):
        return self.data_w/self.total_data_packets
    
    def X_Data(self):
        return self.data_x/self.total_data_packets
    
    def Nq_Data(self):
        return self.data_w/10000
    
    def T_Voice(self):
        return self.voice_t/self.total_voice_packets
    
    def W_Voice(self):
        return self.voice_w/self.total_voice_packets
    
    def Nq_Voice(self):
        return self.voice_w/10000

# Cliente de voz
class Voice(object):
    def __init__(self, env, server, name, collector):
        self.env = env
        self.server = server
        self.name = name
        self.collector = collector
        
        self.mean_silence = 650.0
        self.mean_packet = 22.0
        self.packet_rate = 16
        
        self.action = env.process(self.run())
        
    def run(self):
        # Gera o periodo de silencio e o numero de pacotes a serem enviados
        t = self.silence()
        print('%d ms: %s período de silencio gerado: %d ms' % (env.now, self.name, t))
        yield self.env.process(self.process(t))
        
        while True:
            # Acordando o processo
            print ('%d ms: %s acordou' % (env.now, self.name))
            
            # Enviando pacotes para a fila
            n_packets = self.voice_packet()
            self.collector.total_voice_packets += n_packets
            for i in xrange(0, n_packets):
                yield self.env.process(self.process(self.packet_rate))
                print ('%d ms: %s[%d] entrou na fila' % (env.now, self.name, i))
                packet = VoicePacket(self.env, self.server, self.name, i, self.collector)
                
            # Periodo silencioso
            yield self.env.process(self.process(self.packet_rate))
            t = self.silence()
            print ('%d ms: %s tempo de silencio: %d ms' % (env.now, self.name, t))
            yield self.env.process(self.process(t))
    
        
    # Gera um periodo de silencio
    def silence(self):
        mean = 1.0/self.mean_silence
        prob = random.uniform(0, 1)
        return math.ceil(math.log(prob)/(-mean))
    
    # Gera um numero de pacotes de voz a serem processados
    def voice_packet(self):
        # p = 1/22, q = 1 - 1/22 =~ 0.954545
        q = 1.0 - (1.0/self.mean_packet)
        prob = random.uniform(0, 1)
        return int(math.ceil(math.log(prob)/math.log(q)))
            
    def process(self, duration):
        yield self.env.timeout(duration)


# Pacote de voz    
class VoicePacket(object):
    def __init__(self, env, server, name, i, collector):
        self.env = env
        self.server = server
        self.name = name
        self.i = i
        self.collector = collector
        
        self.t_arrival = 0.0
        self.t_departure = 0.0
        self.t_in_server = 0.0
        
        self.packet_size = 512.0
        self.twoMb = 2097152.0

        self.action = env.process(self.service())
        
    def service(self):
        self.t_arrival = env.now
        # Entra na fila com prioridade 0 (máxima)
        with self.server.request(priority = 0) as req:
            yield req
            self.collector.voice_w += env.now - self.t_arrival
            
            print ('%d ms: %s[%d] sendo processado' % (env.now, self.name, self.i))
            # Tempo de processamento
            yield self.env.process(self.process(1000*self.packet_size/self.twoMb))
            
            # Coleta estatisticas
            self.t_departure = env.now
            self.collector.voice_t += self.t_departure - self.t_arrival
            print ('%d ms: %s[%d] partiu' % (env.now, self.name, self.i))
        
    def process(self, duration):
        yield self.env.timeout(duration)
       
        
# Cliente de dados      
class Data(object):
    def __init__(self, env, server, name, rho, collector):
        self. env = env
        self.server = server
        self.name = name
        
        # Dados calculados analiticamente pela inversa da pdf(x) do pacote de dados
        self.inferior_limit = 0.28663
        self.superior_limit = 0.61337
        self.angle = 0.000208914
        
        self.data_size = [64.0, 512.0, 1500.0]
        self.twoMb = 2097152   # 2Mb
        
        self.rho = rho         # Taxa de utilização do servidor
        self.total_time = 0.0  # Tempo total gasto pelos pacotes de dados para serem processados
        self.id = 0
        
        self.collector = collector
        
        self.action = env.process(self.run())
        
    def run(self):
        self.id = 1        # ID do pacote
        self.collector.total_data_packets += 1
        packet_rate = 100  # Taxa inicial = 1 pacote a cada 100ms
        while True:
            packet_size = self.data_packet()
            t_process = (packet_size*8000)/self.twoMb  # 8 bits * 1000 = taxa em ms 

            packet = DataPacket(self.env, self.server, t_process, self.id, self.collector)
            
            # Envia pacotes de acordo com a taxa de utilização
            yield self.env.process(self.process(packet_rate))
            packet_rate = self.get_rate(packet_rate, env.now, t_process)
            
            self.id += 1
            self.collector.total_data_packets += 1
            
    # Gera um pacote de dados com tamanho variando entre 64 e 1500 bytes, probabilisticamente
    def data_packet(self):
        prob = random.uniform(0, 1)
        x = prob - self.inferior_limit
        
        if(prob < self.inferior_limit):
            return self.data_size[0]
        if(prob >= self.inferior_limit and prob < .4):
            return math.ceil((x)/self.angle)
        if(prob >= .4 and prob < .5):
            return self.data_size[1]
        if(prob >= .5 and prob < self.superior_limit + .1):
            return math.ceil((x - .1)/self.angle)
        else:
            return self.data_size[2]
    
    # Ajustar para preemptivo
    # Ajusta a taxa de chegada para os pacotes de dados de modo que ela fique próxima do Rho escolhido    
    def get_rate(self, packet_rate, time_now, time_process):
        err = 0.00005
        correction = 10
        self.total_time += time_process
        tax = self.total_time/time_now
        
        print tax, packet_rate
        
        if(tax > self.rho + err):
            return packet_rate + correction
        if(tax < self.rho - err):
            if(packet_rate - 10 <= correction):
                return 1
            else:
                return packet_rate - correction
        else:
            return packet_rate
            
    def process(self, duration):
        yield self.env.timeout(duration)


# Pacote de dados       
class DataPacket(object):
    def __init__(self, env, server, t_process, i, collector):
        self.env = env
        self.server = server
        self.t_process = t_process
        self.i = i
        
        self.collector = collector
        
        self.t_arrival = 0.0
        self.t_departure = 0.0
        self.t_in_server = 0.0
        
        self.action = env.process(self.service())
        
    def service(self):
        self.t_arrival = env.now
        print ('%d ms: Pacote de dados[%d] entrou na fila' % (env.now, self.i))
        try:
            with self.server.request(priority = 1) as req:
                yield req
                
                # Entrou no servidor
                print ('%d ms: Pacote de dados[%d] sendo processado.' % (env.now, self.i))
                self.t_in_server = env.now # Tempo que entrou no servidor
                self.collector.data_w += env.now - self.t_arrival # Quanto tempo ficou na fila
                yield self.env.process(self.process(self.t_process)) # Processando
               
                # Coleta quanto tempo o processamento levou
                self.collector.data_x += env.now - self.t_in_server # Quanto tempo ficou processando
                
                # Horario da partida
                self.t_departure = env.now
                self.collector.data_t += self.t_departure - self.t_arrival
                
                print ('%d ms: Pacote de dados[%d] partiu' % (env.now, self.i))
                
        except simpy.Interrupt as interrupt:
            usage = env.now - interrupt.cause.usage_since
            interruption_time = env.now
            print('%d ms: Pacote de dados[%d] foi interrompido depois de %s ms no total' % (interruption_time, self.i, usage))
                
            # Tenta novamente
            packet = DataPacket(self.env, self.server, self.t_process, self.i, self.collector)
    
    def process(self, duration):
        yield self.env.timeout(duration)


if __name__ == "__main__":
    random.seed(42) # Semente inicial
    n_voz = 30 # Número de clientes de voz
    data_rho = 0.5 # Taxa de utilização pelos pacotes de dados
    
    k = 1000 # Numero de coletas por rodada (ajustar mais tarde)
    
    # Inicializa o sistema
    env = simpy.Environment()
    preemptive = False
    if(preemptive):
        server = simpy.PreemptiveResource(env, capacity=1)
    else:
        server = simpy.PriorityResource(env, capacity=1)
 
    # Coletor de estatísticas
    collector = StatisticsCollector()  
    
    # Inicializa os clientes de voz
    for i in xrange(0, n_voz):    
        voice = Voice(env, server, 'Voice[%s]' % i, collector)
  
    # Inicializa o cliente de dados    
    data = Data(env, server, 'Data', data_rho, collector)

    # Roda a simulação
    env.run(until=10000)
    
    # Analisa dados coletados
    print collector.T_Data()
    print collector.W_Data()
    print collector.X_Data()
    print collector.Nq_Data()
    print
    print collector.T_Voice()
    print collector.W_Voice()
    print collector.Nq_Voice()
    print collector.data_x/10000
    