# -*- coding: utf-8 -*-
import math
import random
import simpy

# TODO: terminar as implementações com os tempos corretos
#       calcular os dados finais

class Voice(object):
    def __init__(self, env, server, name, prio):
        self.env = env
        self.server = server
        self.name = name
        self.prio = prio
        
        self.mean_silence = 755.0
        self.mean_packet = 22.0
        
        self.action = env.process(self.run())
        
    def run(self):
        t = self.silence()
        print('%s período de silencio inicial: %d ms' % (self.name, t))
        yield self.env.process(self.process(t))
        
        while True:
            # Chegando na fila
            print ('%s chegando na fila no tempo %d ms' % (self.name, env.now))
                
            # Entra na fila (com prioridade)
            req = self.server.request(priority = self.prio)
            yield req
                
            # Assim que chega sua vez, começa a ser processado
            print ('%s sendo processado no tempo %d ms' % (self.name, env.now))
            yield self.env.process(self.process(500))
            server.release(req)
            print ('%s partiu no tempo %d ms' % (self.name, env.now))
                
            # Fica em silencio por um periodo e depois volta a ativadade
            t = self.silence()
            print ('%s tempo de silencio: %d ms' % (self.name, t))
            yield self.env.process(self.process(t))
                
            # Teste para finalizar a simulação
            # TODO: critério de parada
            '''
            if(env.now >= 3000):
                print ("Terminando")
                break
            '''
        
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
        return math.ceil(math.log(prob)/math.log(q))
            
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
        
        self.data_packet = [64, 512, 1500]
        
        self.action = env.process(self.run())
        
    def run(self):
        while True:
            try:
                # Entra na fila (com prioridade)
                req = self.server.request(priority = self.prio)
                yield req
                
                # Assim que chega sua vez, começa a ser processado
                print ('%s sendo processado no tempo %d ms' % (self.name, env.now))
                yield self.env.process(self.process(300))
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
            return self.data_packet[0]
        if(prob >= self.inferior_limit and prob < .4):
            return math.ceil((x)/self.angle)
        if(prob >= .4 and prob < .5):
            return self.data_packet[1]
        if(prob >= .5 and prob < self.superior_limit + .1):
            return math.ceil((x - .1)/self.angle)
        else:
            return self.data_packet[2]
        
    def process(self, duration):
        yield self.env.timeout(duration)

if __name__ == "__main__":
    n_voz = 1
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
    env.run(until=3000)