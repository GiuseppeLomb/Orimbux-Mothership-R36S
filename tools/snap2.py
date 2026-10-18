import ctypes, os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)
for f in ("pet.json", "config.json"):
    try: os.remove(os.path.join(APPD, f))
    except OSError: pass
import sdl2
from PIL import Image
import app as appmod
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready: time.sleep(0.05)
def snap(name, frames=3, dt=1/30.0):
    for _ in range(frames): a.frame(dt)
    buf = ctypes.create_string_buffer(640*480*4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640*4)
    Image.frombuffer("RGBA",(640,480),buf.raw,"raw","RGBA",0,1).convert("RGB").save(os.path.join(OUT,name+".png"))
    sdl2.SDL_RenderPresent(a.ren)
a.go("bridge"); snap("b_music", 20)
a.cur.on("press","r1"); snap("b_games", 20)
a.cur.on("press","r1"); snap("b_system", 20)
pet = a.sections["pet"]
a.go("pet"); snap("p0_egg", 5)
import pet as petmod
pet.tick(petmod.HATCH_AT+10)
a.cur.process_events(); snap("p1_name", 5)
pet.on("press","a"); snap("p2_baby", 10)
pet.p["poops"]=2; pet.p["full"]=20; pet.on("press","right"); snap("p3_hungry", 5)
pet.sel=0; pet.on("press","a"); snap("p4_feed", 2); pet.on("press","a"); snap("p5_eating", 8)
pet.anim=None; pet.sel=1; pet.on("press","a"); assert pet.mode=="game", pet.mode
for i in range(90): pet.update_game(1/30.0)
snap("p6_game", 2)
pet.end_game(); pet.sel=6; pet.on("press","a"); snap("p7_stats", 2); pet.on("press","a")
# grow to teen and adult
pet.tick(petmod.TEEN_AT); pet.process_events(); snap("p8_evolve", 2)
pet.anim=("evolve", time.time()-4, pet.anim[2]); snap("p9_evolved", 2); pet.finish_event()
pet.p["age"]=petmod.ADULT_AT+5; pet.tick(1); pet.process_events(); pet.finish_event(); snap("p10_adult", 10)
pet.p["lights_off"]=True; pet.p["sleeping"]=True; snap("p11_sleep", 4)
for f in ("nebulon","glorpo","snarx"):
    pet.p["form"]=f; pet.p["sleeping"]=False; pet.p["lights_off"]=False; snap("p12_"+f, 4)
pet.away_report={"gap":9*3600,"before":{"poops":0,"full":80,"happy":80,"form":"glorpo"},"after":{"poops":2,"full":25,"happy":40,"form":"glorpo"},"got_sick":True}
pet.mode="away"; snap("p13_away", 2); pet.mode="home"
pet.anim=("depart", time.time()-5, "old"); pet.mode="event"; snap("p14_depart", 2)
pet.finish_event(); snap("p15_memorial", 3)
pet.p["history"].append({"gen":0,"name":"KIKI","form":"snarx","days":12.3,"reason":"sick","hue":0.5})
pet.msel=1; pet.mode="memorial_del"; snap("p16_delete", 2); pet.mode="home"
a.go("bridge"); snap("b_widget_egg", 5)
pet.p.update({"form":"glorpo","name":"MOMO","full":15,"hue":0.3}); pet.prev_needs=set(); pet.update(0.01); a.go("bridge"); snap("b_widget", 8)
a.go("pet"); pet.prev_needs=set(); pet.p["full"]=15; pet.update(0.01); snap("p17_bubble", 10)
d = a.sections["trailer"]; d.force_t = 0.0; a.go("trailer")
BAR = 60/140*4
for nm, bar in (("d0_intro",1.0),("d1_logo",3.4),("d2_app",9.0),("d3_mosaic",29.0),("d4_end",31.5)):
    d.force_t = bar*BAR; snap(nm, 3)
print("ok")
a.go("pet"); pet.away_report=None; pet.mode="home"; pet.msg=""
for need,setup in (("fome",{"full":10}),("sono",{"full":80,"energy":14}),("sujo",{"energy":80,"poops":3,"hygiene":20})):
    pet.p.update(setup); pet.p["sick"]=False; pet.p["sleeping"]=False; pet.prev_needs=set(); pet.last_call=0; pet.update(0.01)
    pet.note=(pet.note[0], time.time()-0.6); snap("n_"+need, 3)
pet.mode="memorial"; pet.msel=0; snap("p18_memorial2", 3)
print("ok2")
