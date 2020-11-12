
#pip install gputil
import GPUtil 
import math
import time
import random
import hashlib
import requests
import subprocess
PRIMENET_USERID = "baabaagoat"# <-- your primenet user id here
"""
USING:GET URL      template_server + AddPrimenetCipher(template_xxx%(xxx),GUID)   to push commands to server
PARAMS:

template_po%(GUID)  --> tell server "I want trial factoring ONLY",needs AddPrimenetCipher
template_uc%(GUID,HASH_HW,HASH_SW,GPUtil.getGPUs()[0].name.replace(" ","+"),PRIMENET_USERID)   --> register computer to server&bind primenet user id,do this ONLY ONCE,needs AddPrimenetCipher,
    HASH_HW HASH_SW can be random
    PRIMENET_USERID is your primenet id
template_ga%(GUID) --> tell server "I want a exponent to work on"
    server return:
	pnErrorResult=0
	pnErrorDetail=Server assigned trial factoring work.
	g=eb03aebb5d8ef55cf1436800db1d4155  --> your GUID
	k=E19A3FF87A860F89D351E54B3E4DAB96  --> task ID
	A=1
	b=2
	n=204255473                         --> exponent to work on
	c=-1
	w=2
	sf=73                               --> will try factors in 2^sf ~ 2^ef 
	ef=74
	==END==
template_ar_fail%(GUID,TASKID,n,sf,ef) --> tell server "Mn have no factor  in 2^sf ~ 2^ef
template_ar_fail%(GUID,TASKID,n,X,sf) --> tell server "Mn have factor X in 2^sf ~ 2^ef
    n sf ef TASKID must be same as what you've got
    
for any commands:server return pnErrorResult=0 --> success
"""
template_server = "http://v5.mersenne.org/v5server/?";
template_uc = "v=0.95&px=GIMPS&t=uc&g=%s&hg=%s&wg=%s&a=Windows64,Prime95,v30.3,build+6&c=%s&f=CUDA,&L1=0&L2=0&np=1&hp=1&m=32768&s=5000&h=24&r=1000&L3=16384&u=%s&cn=GPU+TF";
template_po = "v=0.95&px=GIMPS&t=po&g=%s&nw=1&w=2&Priority=1&DaysOfWork=3&DayMemory=256&NightMemory=256&DayStartTime=450&NightStartTime=1410&RunOnBattery=1";
template_ga = 	"v=0.95&px=GIMPS&t=ga&g=%s&c=0&disk=6.000000";
template_ar_fail = "v=0.95&px=GIMPS&t=ar&g=%s&k=%s&r=4&d=1&m=&n=%s&sf=%s&ef=%s";
template_ar_succ = "v=0.95&px=GIMPS&t=ar&g=%s&k=%s&r=1&d=1&m=&n=%s&f=%s&sf=%s";

        
logfile = open("Logfile.log","w+");
def AddPrimenetCipher(cmd,GUID):
    # by reverse-engineering on prime95 30.3
    cmd = cmd + "&ss=%d&"%math.floor(random.random() * 32767)
    PostData = bytearray(hashlib.new('md5', GUID.lower().encode("ASCII")).digest());
    for i in range(0,16):
        PostData[i] = PostData[i] ^ (PostData[(PostData[i]^0x49)%0x10]^0x45);
    PostData = hashlib.new('md5', PostData).hexdigest().upper();
    cmd = cmd + "sh=%s"%(hashlib.new('md5', (cmd + PostData).encode("ASCII")).hexdigest().upper())
    return cmd
def PrimenetPushCommandTillSuccess(cmd):
    for i in range(10):
        try:
            print(time.asctime() + " I " + "Primenet:Tx "+cmd,file=logfile)
            reply = requests.get(cmd).content.decode("ASCII");
            print(reply)
            assert("pnErrorResult=0" in reply);
            print(time.asctime() + " I " + "Primenet:Rx "+reply,file=logfile)
            return reply
        except:pass
    print(time.asctime() + " E " + "Primenet:Fail after 10 retries for command: "+cmd,file=logfile)
    return None    
# Open File to get GUID
try:
    with open("GUID.ini","r") as f:
        GUID = f.read(32);
        assert(len(GUID) == 32)
        print(time.asctime() + " I " + "got GUID:"+GUID+" from file succeed",file=logfile)
except:
    GUID = ''.join([random.choice('0123456789abcdef') for i in range(32)])
    HASH_HW = ''.join([random.choice('0123456789ABCDEF') for i in range(32)])
    HASH_SW = ''.join([random.choice('0123456789ABCDEF') for i in range(32)])
    PrimenetPushCommandTillSuccess(template_server + AddPrimenetCipher(template_uc%(GUID,HASH_HW,HASH_SW,GPUtil.getGPUs()[0].name.replace(" ","+"),PRIMENET_USERID),GUID))
    with open("GUID.ini","w") as f:
        f.write(GUID)
    print(time.asctime() + " I " + "ask for GUID:"+GUID+" from primenet succeed",file=logfile)
PrimenetPushCommandTillSuccess(template_server + AddPrimenetCipher(template_po%(GUID),GUID));

while True:
    task = PrimenetPushCommandTillSuccess(template_server + AddPrimenetCipher(template_ga%(GUID),GUID));
    result = dict();
    for i in task.split("\n"):
        if("k=" in i):result['k'] = i[2:];
        if("n=" in i):result['n'] = i[2:];
        if("sf=" in i):result['sf'] = i[3:];
        if("ef=" in i):result['ef'] = i[3:];
    print(time.asctime() + " I " + "got TASK:"+result['k'] +","+result['n']+","+result['sf']+","+result['ef'],file=logfile)

    child = subprocess.Popen(['mfaktc-win-64.exe','-tf',result['n'],result['sf'],result['ef']],stdout=subprocess.PIPE)
    factor = None;
    while True:
        stat = child.poll() is not None;
        output = child.stdout.readline().decode("ASCII");
        print(output,end="")
        if("has a factor:" in output):
            foundfactor = True;
            factor = output.find("has a factor:") + len("has a factor:")+1
            factor = output[factor:output.find("\n",factor)];
            child.terminate();
            break;
        if(stat):
            child.stdout.close()
            break;
    if(factor is None):
        PrimenetPushCommandTillSuccess(template_server + template_ar_fail%(GUID,result['k'],result['n'],result['sf'],result['ef']));
        print(time.asctime() + " I " + "M%s have no factor between 2^%s~2^%s"%(result['n'],result['sf'],result['ef']),file=logfile)
    else:
        PrimenetPushCommandTillSuccess(template_server + template_ar_succ%(GUID,result['k'],result['n'],factor,result['sf']));
        print(time.asctime() + " I " + "M%s have factor %s between 2^%s~2^%s"%(result['n'],factor,result['sf'],result['ef']),file=logfile)