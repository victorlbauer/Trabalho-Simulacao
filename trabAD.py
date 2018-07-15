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
        
        self.action = env.process(self.run())
        
    def run(self):
        while True:
            with self.server.request() as req:
                yield req
                print ('%s[%d] sendo processado' % (self.name, self.i))
                yield self.env.process(self.process(100))
                print ('%s[%d] partiu. T = %d ms' % (self.name, self.i, env.now))
            break
        
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
        print('%s período de silencio inicial: %d ms' % (self.name, t))
        yield self.env.process(self.process(t))
        
        while True:
            # Acordando o processo
            print ('%s acordou. T = %d ms' % (self.name, env.now))
            
            # Enviando pacotes para a fila
            print ('%s começou a enviar pacotes para a fila. T = %d ms' % (self.name, env.now))
            for i in xrange(0, 3):
                yield self.env.process(self.process(self.packet_rate))
                print ('%s[%d] entrou na fila. T = %d ms' % (self.name, i, env.now))
                packet = VoicePacket(self.env, self.server, self.name, i)
                
    
            t = self.silence()
            print ('%s tempo de silencio: %d ms' % (self.name, t))
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
            try:
                # Taxa de chegada = 10% de utilização
                yield env.timeout(100)
                
                # Entra na fila (com prioridade)
                req = self.server.request(priority = self.prio)
                yield req
                
                # Assim que chega sua vez, começa a ser processado
                t_processo = self.data_packet()/self.twoMB
                print ('Sendo processado no tempo %d ms. Tempo de serviço = %f' % (env.now, t_processo))
                yield self.env.process(self.process(t_processo))
                server.release(req)
                
            except simpy.Interrupt as interrupt:
                by = interrupt.cause.by
                usage = env.now - interrupt.cause.usage_since
                print('%s foi interrompido por %s, no tempo %s ms, depois de %s ms' % (self.name, by, env.now, usage))
    
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
         
    #q = Queue(env, server, queue)
    # Inicializa o cliente de dados    
    #data = Data(env, server, 'Data', 1)
    
    # Roda a simulação
    env.run(until=2000)