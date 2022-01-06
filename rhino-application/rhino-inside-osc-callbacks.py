#tested with python3.7
import rhinoinside
rhinoinside.load()
from pathlib import Path
import clr

sysdir = Path(r"C:\Program Files\Rhino 7\System")
plugdir = Path(sysdir, "..", "Plug-ins").resolve()
rhinoinside.load(f"{sysdir}")

GrasshopperDll = f'{Path(plugdir, "Grasshopper", "Grasshopper.dll").resolve()}'
GH_IODll= f'{Path(plugdir, "Grasshopper", "GH_IO.dll")}'
GH_UtilDll= f'{Path(plugdir, "Grasshopper", "GH_Util.dll")}'

clr.AddReference(GrasshopperDll)
clr.AddReference(GH_IODll)
clr.AddReference(GH_UtilDll)

# Set up ready, now do the actual Rhino usage

import System
import Rhino

from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import Grasshopper
from Grasshopper.Kernel import GH_Document, GH_SolutionMode, GH_Component
from GH_IO.Serialization import GH_Archive
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper.Kernel.Types import GH_Number, GH_String, GH_Integer
import time
import json

print("Finished Loading Libs")


start = time.time()
definition = GH_Document()
archive = GH_Archive()
archive.ReadFromFile(r"./operations.gh")
middle = time.time()


archive.ExtractObject(definition, "Definition")
end = time.time()

print(f"start = {middle-start}")
print(f"end= {end-middle}")

print("Finished loading Document")

args_typecasters = {'integer':lambda x: GH_Integer(int(x)), 'number' : lambda x: GH_Number(float(x)), 'string': GH_String }

results_typecasters = {'Vector3D': lambda v: [v.X, v.Y, v.Z]}

def commandHandler(addr,additional_args,payload): 
    print("\n\n\n")
    client=additional_args[0]
    data = json.loads(payload)
    callbackName = data['ghCallback']
    args = data['args']
    outs = data['outs']
    nicknames = {'sun-weather' : 'SunVectorCalculatorWeatherFile', 'sun-coords': 'SunVectorCalculatorLatLong'}
    objectNickName =  nicknames[callbackName]
    gh_obj = None
    for ob in definition.Objects:
        if ob.NickName == objectNickName:
            gh_obj = ob
            break
    
    for input in gh_obj.Params.Input:
        if input.NickName in args.keys():
            input.VolatileData.Clear()
            arg = args[input.NickName]
            gh_param = args_typecasters[arg['type']](arg['value'])
            print(input.NickName)
            print(gh_param)
            input.AddVolatileData(GH_Path(0), 0, gh_param)

    definition.NewSolution(True, GH_SolutionMode.Silent)

    response = {"id":0, "ghCallback": callbackName, "results": {}}

    results = response['results']
    for output in gh_obj.Params.Output:
        if output.NickName in outs.keys():
            print(f"Computing {output.NickName}")
            result_type = outs[output.NickName]
            caster = results_typecasters[result_type]
            output.CollectData()
            output.ComputeData()
            results[output.NickName] = []

            pathcount = output.VolatileData.PathCount
            print(pathcount)
            idx = 0
            while idx < pathcount:
                b = output.VolatileData.get_Branch(idx)
                print(b)
                for item in b:
                    print(item)
                    results[output.NickName].append(caster(item.Value))
                idx = idx + 1
            
            if len(results[output.NickName]) == 1:
                results[output.NickName] = results[output.NickName][0]
    gh_obj.ClearData()
    # definition.ExpireSolution()
    response = json.dumps(response)
    client.send_message("/response", response)

client = udp_client.SimpleUDPClient("127.0.0.1",3334)
dispatcher = dispatcher.Dispatcher()
dispatcher.map("/compute", commandHandler, client)

server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 3335), dispatcher)

server.serve_forever()


