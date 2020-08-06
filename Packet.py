#Packets contain a source IP of the router that created them and a payload that is the data or message being sent.  Utilizing pickles allows us to turn the pacet structure to a sendable array of bytes that can be converted back to the initial packet.
import pickle
import pickletools

class Pack:
    src = ""
    payload = ""
    def tobytes(self):
        byt = pickle.dumps(self)
        return pickletools.optimize(byt)

def frombytes(byt):
    return pickle.loads(byt)

class DijkPack(Pack):
    dest = None

class FloodPack(Pack):
    seq = 0
