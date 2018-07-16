# -*- coding: utf-8 -*-
import math
import random
import simpy

# TODO: terminar as implementações com os tempos corretos
#       calcular os dados finais

class VoicePacket(object):
    def __init__(self, env, server, name, i):
        self.env = env
        self.server = server
        self.name = name
        self.i = i
        
        self.action = env.process(self.service())
        
    def service(self):
        # Entra na fila com prioridade 0 (máxima)
        with self.server.request(priority = 0) as req:
            yield req
            print ('%d ms: %s[%d] sendo processado' % (env.now, self.name, self.i))
            # Tempo de processamento
            yield self.env.process(self.process(100))
            print ('%d ms: %s[%d] partiu' % (env.now, self.name, self.i))
        
    def process(self, duration):
        yield self.env.timeout(duration)
        
        
class DataPacket(object):
    def __init__(self, env, server, t_process):
        self.env = env
        self.server = server
        self.t_process = t_process
        self.action = env.process(self.service())
        
    def service(self):
        print ('%d ms: Pacote de dados entrou na fila' % env.now)
        try:
            with self.server.request(priority = 1) as req:
                yield req
                # Assim que chega sua vez, começa a ser processado
                print ('%d ms: Pacote de dados sendo processado. Tempo de serviço = %f' % (env.now, self.t_process))
                yield self.env.process(self.process(self.t_process))
                print ('%d ms: Pacote de dados partiu' % env.now)
                
        except simpy.Interrupt as interrupt:
            #by = interrupt.cause.by
            usage = env.now - interrupt.cause.usage_since
            interruption_time = env.now
            print('%d ms: Um pacote de dados foi interrompido depois de %s ms após o início de seu processamento' % (interruption_time, usage))
                
            # Tenta novamente
            self.service()
    
        
    def process(self, duration):
        yield self.env.timeout(duration)

    
class Voice(object):
    def __init__(self, env, server, name, prio):
        self.env = env
        self.server = server
        self.name = name
        self.prio = prio
        
        self.mean_silence = 650.0
        self.mean_packet = 22.0
        self.packet_rate = 16
        
        self.action = env.process(self.run())
        
    def run(self):
        t = self.silence()
        print('%d ms: %s período de silencio inicial: %d ms' % (env.now, self.name, t))
        yield self.env.process(self.process(t))
        
        while True:
            # Acordando o processo
            print ('%d ms: %s acordou' % (env.now, self.name))
            
            # Enviando pacotes para a fila
            print ('%d ms: %s começou a enviar pacotes para a fila' % (env.now, self.name))
            for i in xrange(0, 3):
                yield self.env.process(self.process(self.packet_rate))
                print ('%d ms: %s[%d] entrou na fila' % (env.now, self.name, i))
                packet = VoicePacket(self.env, self.server, self.name, i)
                
            # Periodo silencioso
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
        
        
class Data(object):
    def __init__(self, env, server, name, prio):
        self. env = env
        self.server = server
        self.name = name
        self.prio = prio
        
        # Dados calculados analiticamente
        self.inferior_limit = 0.28663
        self.superior_limit = 0.61337
        self.angle = 0.000208914
        
        self.data_size = [64, 512, 1500]
        self.twoMB = 2097152.0 # 2MB = 2.097.152 bytes
        
        self.action = env.process(self.run())
        
    def run(self):
        while True:
            t_processo = self.data_packet()/self.twoMB
            
            packet = DataPacket(self.env, self.server, 120)
            
            # Um pacote a cada 100 ms
            yield self.env.process(self.process(100))

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
        
    def process(self, duration):
        yield self.env.timeout(duration)

if __name__ == "__main__":
    n_voz = 2
    env = simpy.Environment()
    preemptive = True
    
    if(preemptive):
        server = simpy.PreemptiveResource(env, capacity=1)
    else:
        server = simpy.PriorityResource(env, capacity=1)
     
    # Inicializa os clientes de voz
    for i in xrange(0, n_voz):    
        voice = Voice(env, server, 'Voice[%s]' % i, 0)
         
    # Inicializa o cliente de dados    
    data = Data(env, server, 'Data', 1)
    
    # Roda a simulação
    env.run(until=2000)