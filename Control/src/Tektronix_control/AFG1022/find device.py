import pyvisa

rm = pyvisa.ResourceManager()
r = rm.list_resources()
print(r)