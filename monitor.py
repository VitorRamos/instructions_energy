from peachpy import *
from peachpy.x86_64 import *
from peachpy.literal import Constant
from util import *
from profiler import *
import pandas as pd
import numpy as np

prof= Profiler([["PERF_COUNT_HW_INSTRUCTIONS"], ["SYSTEMWIDE:RAPL_ENERGY_PKG"]])
prof.start_counters(pid=0)

def is_valid_instruction(inst, args):
    try:
        with Function("main", (), int32_t, target=uarch.default + isa.avx + isa.sse4_2) as asm_function:
            inst(*args)
            RETURN(0)
        asm_function.finalize(abi.detect())
    except:
        return False
    return True

def energy_consumed_inst(insts, args, rep= 30, verbose=0):
    df= []
    for inst in insts:

        if verbose:
            print(inst(*args[0]).name)

        for arg in args:
            with Function("main", (), int32_t, target=uarch.default + isa.avx + isa.sse4_2) as asm_function:
                XOR(rcx,rcx)
                MOV(rax, 1)
                MOV(rdx, 0)
                myl= Label("loop")

                LABEL( myl )
                for _ in range(10):
                    inst(*arg)
                ADD(rcx, 1)
                CMP(rcx, 9999999)
                JNE( myl )

                RETURN(0)

            python_function = asm_function.finalize(abi.detect()).encode().load()

            data= []
            for _ in range(rep):
                prof.reset_events()
                prof.enable_events()
                python_function()
                prof.disable_events()
                data.append(prof.read_events())

            data= np.array(data).reshape(-1,2)
            row= [inst(*arg).name, list(map(str,arg)), data.mean(axis=0).astype(int)[1] ]
            df.append(row)

            if verbose:
                print(list(map(str,arg)), data.mean(axis=0).astype(int), (data.std(axis=0)/data.mean(axis=0)*100).astype(int))

    return df

def supported_inst(insts, args):
    suported, unsuported, wrong_arg= 0, 0, 0
    for inst in insts:
        wrong_arg_flag= True
        for arg in args:
            try:
                with Function("main", (), int32_t, target=uarch.default + isa.avx + isa.sse4_2) as asm_function:
                    inst(*arg)
                    RETURN(0)
                asm_function.finalize(abi.detect())
                # print("Supported", inst(*arg).name, arg)
                suported+=1
                wrong_arg_flag= False
                break
            except Exception as e:
                if "Invalid operand types" in str(e):
                    # print("Unsupported", inst(*arg).name, arg)
                    pass
                if "is not supported on the target" in str(e):
                    #print(e)
                    wrong_arg_flag= False
                    unsuported+=1
                    break
        if wrong_arg_flag:
            # print("Wrong arg", inst)
            wrong_arg+=1

    print( "Total {}, Supported {}, Unsupported {}, Wrong arg {} ".format(len(insts), suported, unsuported, wrong_arg) )

def monitor_cpu(insts, args, csv_name):
    for inst in insts:
        for arg in args:
            if is_valid_instruction(inst, arg):
                if os.path.isfile(csv_name):
                    df= pd.read_csv(csv_name)
                    if df[ (df["inst"].str.contains(inst(*arg).name)) &  (df["args"] == str(list(map(str,arg))) ) ].shape[0] != 0: 
                        continue
                else:
                    pd.DataFrame([],columns=["inst","args","energy"]).to_csv(csv_name,index=False)

                df= energy_consumed_inst([inst], [arg], verbose=1)
                pd.DataFrame(df,columns=["inst","args","energy"]).to_csv(csv_name,mode="a",header=False, index=False)


# supported_inst(generic, args_generic)
# monitor_cpu(generic, args_generic, "generic.csv")
# supported_inst(mmxsse, mmxsse_args)
# monitor_cpu(mmxsse, mmxsse_args, "mmx.csv")
# supported_inst(avx, avx_args)
monitor_cpu(avx, avx_args, "avx.csv")