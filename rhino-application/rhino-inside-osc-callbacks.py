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
from Grasshopper.Kernel import GH_Document, GH_SolutionMode, GH_Component, Special
from GH_IO.Serialization import GH_Archive
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper.Kernel.Types import GH_Number, GH_String, GH_Integer
import time
import json
print("Finished Loading Libs")

definition = GH_Document()
archive = GH_Archive()
archive.ReadFromFile(r"./rhino-application/operations.gh")
archive.ExtractObject(definition, "Definition")
print("Finished loading Document")


# Cast input/output data based off of argument type
args_typecasters = {'integer':lambda x: GH_Integer(int(x)), 'number' : lambda x: GH_Number(float(x)), 'string': GH_String, 'json': lambda x: GH_String(json.dumps(x)) }
results_typecasters = {'Vector3D': lambda v: [v.X, v.Y, v.Z], 'number' : lambda x: x, 'string': lambda x: x}

# Register objects/clusters in the definition to keys
nicknames = {'sun-weather' : 'SunVectorCalculatorWeatherFile', 'sun-coords': 'SunVectorCalculatorLatLong', 'cost-calculator': "CostCalculator", "calculate-eui": "EUIComputer"}


def commandHandler(addr,additional_args,payload): 
    print("\n\n\n")
    client=additional_args[0] # Where to send response to
    data = json.loads(payload) # The data
    callbackName = data['ghCallback'] # Use this to identify which object to call
    print(callbackName)
    args = data['args'] # The arguments, with type and value data
    outs = data['outs'] # the outputs to cull, with type data

    # Get the object nickname, if it's not registered bail out
    try: 
        objectNickName =  nicknames[callbackName]
    except KeyError:
        print("Command not supported.")
        return

    # Get the GH object by its nickname.  There should be a better way to do this...
    # Bail out if it's not found
    gh_obj = None
    for ob in definition.Objects:
        if ob.NickName == objectNickName:
            gh_obj = ob
            if type(gh_obj) == Special.GH_Cluster:
                gh_obj.CreateFromFilePath(f'./rhino-application/{objectNickName}.ghcluster')
                gh_obj.ExpireSolution(False)
                # print(dir(gh_obj))
                # gh_obj.NewSolution(True, GH_SolutionMode.Silent)
            break
    if gh_obj == None:
        print("Command not supported")
        return

    
    # Clear and update input data.
    for input in gh_obj.Params.Input:
        if input.NickName in args.keys():
            input.VolatileData.Clear()
            arg = args[input.NickName]
            gh_param = args_typecasters[arg['type']](arg['value'])
            print(input.NickName)
            print(gh_param)
            input.AddVolatileData(GH_Path(0), 0, gh_param)

    definition.NewSolution(True, GH_SolutionMode.Silent)


    # Set up the resonse table
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
        else:
            print(output.NickName)
            print("Could not find the above in keys")
        
    # Cleanup
    gh_obj.ClearData()
    gh_obj.ExpireSolution(False)

    # Respond to client
    response = json.dumps(response)
    client.send_message("/response", response)

# Configure the client
client = udp_client.SimpleUDPClient("127.0.0.1",3334)



# Configure the server
dispatcher = dispatcher.Dispatcher()
dispatcher.map("/compute", commandHandler, client)
server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 3335), dispatcher)

server.serve_forever()


