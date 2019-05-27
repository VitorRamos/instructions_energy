from peachpy import *
from peachpy.x86_64 import *
from profiler import *
from matplotlib import pyplot as plt
from peachpy.literal import Constant
import pandas as pd

prof= Profiler([["PERF_COUNT_HW_INSTRUCTIONS"], ["SYSTEMWIDE:RAPL_ENERGY_PKG"]])
prof.start_counters(pid=0)

def is_valid_instruction(inst, args):
    try:
        with Function("main", (), int32_t) as asm_function:
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
            with Function("main", (), int32_t) as asm_function:
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
            row= [inst(*arg).name, str(arg), data.mean(axis=0).astype(int)[1] ]
            df.append(row)

            if verbose:
                print(arg, data.mean(axis=0).astype(int), (data.std(axis=0)/data.mean(axis=0)*100).astype(int))

    return df

def supported_inst(insts, args):
    suported, unsuported, wrong_arg= 0, 0, 0
    for inst in insts:
        wrong_arg_flag= True
        for arg in args:
            try:
                with Function("main", (), int32_t) as asm_function:
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

    print(len(insts), suported, unsuported, wrong_arg)

def monitor_cpu(insts, args, csv_name):
    for inst in insts:
        for arg in args:
            if is_valid_instruction(inst, arg):
                if os.path.isfile(csv_name):
                    df= pd.read_csv(csv_name)
                    if df[ (df["inst"].str.contains(inst(*arg).name)) &  (df["args"] == str(arg) ) ].shape[0] != 0: 
                        continue
                else:
                    pd.DataFrame([],columns=["inst","args","energy"]).to_csv(csv_name,index=False)

                df= energy_consumed_inst([inst], [arg], verbose=1)
                pd.DataFrame(df,columns=["inst","args","energy"]).to_csv(csv_name,mode="a",header=False, index=False)

general_purposed= [ADD, SUB, ADC, SBB, ADCX, ADOX, AND, OR, XOR, ANDN, NOT, NEG,
        INC, DEC, TEST, CMP, MOV, MOVZX, MOVSX, MOVSXD, MOVBE, MOVNTI,
        BT, BTS, BTR, BTC, POPCNT, BSWAP, BSF, BSR, LZCNT, TZCNT, SHR,
        SAR, SHL, SAL, SHRX, SARX, SHLX, SHRD, SHLD, ROR, ROL, RORX, RCR,
        RCL, IMUL, MUL, MULX, IDIV, DIV, LEA, POPCNT, LZCNT,
        TZCNT, BEXTR, PDEP, PEXT, BZHI, BLCFILL, BLCI, BLCIC, BLCMSK, BLCS,
        BLSFILL, BLSI, BLSIC, BLSMSK, BLSR, T1MSKC, TZMSK, CRC32, CBW, CDQ,
        CQO, CWD, CWDE, CDQE, CMOVA, CMOVNA, CMOVAE, CMOVNAE, CMOVB, CMOVNB,
        CMOVBE, CMOVNBE, CMOVC, CMOVNC, CMOVE, CMOVNE, CMOVG, CMOVNG, CMOVGE,
        CMOVNGE, CMOVL, CMOVNL, CMOVLE, CMOVNLE, CMOVO, CMOVNO, CMOVP, CMOVNP,
        CMOVS, CMOVNS, CMOVZ, CMOVNZ, CMOVPE, CMOVPO, SETA, SETNA, SETAE, SETNAE,
        SETB, SETNB, SETBE, SETNBE, SETC, SETNC, SETE, SETNE, SETG, SETNG, SETGE,
        SETNGE, SETL, SETNL, SETLE, SETNLE, SETO, SETNO, SETP, SETNP, SETS, SETNS,
        SETZ, SETNZ, SETPE, SETPO, JA, JNA, JAE, JNAE, JB, JNB, JBE, JNBE, JC, JNC,
        JE, JNE, JG, JNG, JGE, JNGE, JL, JNL, JLE, JNLE, JO, JNO, JP, JNP, JS, JNS,
        JZ, JNZ, JPE, JPO, JMP, JRCXZ, JECXZ, PAUSE, NOP, INT,
        RDTSC, RDTSCP, STC, CLC, CMC, CLD, XADD, XCHG, CMPXCHG,
        CMPXCHG8B, CMPXCHG16B, SFENCE, MFENCE, LFENCE, PREFETCHNTA, PREFETCHT0, PREFETCHT1,
        PREFETCHT2, PREFETCH, PREFETCHW, PREFETCHWT1, CLFLUSH, CLFLUSHOPT, CLWB, CLZERO]
        
general_purposed_2= [PUSH, POP, RET, CALL, UD2, CPUID, XGETBV, SYSCALL, STD]

args= [
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(0), GeneralPurposeRegister64(0)],
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(0), GeneralPurposeRegister64(1)],
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(1), GeneralPurposeRegister64(2)],
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(1), 0],
    
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(0)],
    [GeneralPurposeRegister64(0), GeneralPurposeRegister64(1)],
    [GeneralPurposeRegister64(0), 0],
    
    [GeneralPurposeRegister64(0)],
    
    [GeneralPurposeRegister8(0)],
    
    [],
    
    [GeneralPurposeRegister64(0), GeneralPurposeRegister32(0)],
    [GeneralPurposeRegister64(0), GeneralPurposeRegister16(0)],
    
    [GeneralPurposeRegister64(0), Constant.uint64(1)],
    [Constant.uint64(1), GeneralPurposeRegister64(0)],
    
    [Constant.uint64(1)],
    
    [Constant.uint64x2(1,1)],
]

# supported_inst(general_purposed, args)
monitor_cpu(general_purposed, args, "energy_inst_1.csv")