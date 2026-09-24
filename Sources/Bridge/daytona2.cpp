// GPL-3.0-or-later. Standalone serial Model 3 engine and native macOS platform.
#include <GL/glew.h>
#include <OpenGL/OpenGL.h>
#include <CommonCrypto/CommonDigest.h>
#include "Supermodel.h"
#include "Model3/Model3.h"
#include "Graphics/New3D/New3D.h"
#include "Graphics/Render2D.h"
#include "Graphics/FBO.h"
#include "GameLoader.h"
#include "Inputs/Inputs.h"
#include "Inputs/Input.h"
#include "OSD/Audio.h"
#include "DefaultConfig.h"
#include "media_identity.h"
#if __has_include("settings_identity.h")
#include "settings_identity.h"
#define DAYTONA2_HAS_SETTINGS_SEED 1
#endif
#include <filesystem>
#include <fstream>
#include <memory>
#include <vector>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace fs=std::filesystem;
struct daytona2_context {
 Util::Config::Node config=DefaultConfig();
 std::unique_ptr<CModel3> model;
 std::unique_ptr<CInputs> inputs;
 std::unique_ptr<SuperAA> aa;
 std::unique_ptr<CRender2D> r2;
 std::unique_ptr<New3D::CNew3D> r3;
 CGLContextObj gl=nullptr;
 FBO framebuffer;
 std::string error, saves;
 std::vector<uint8_t> pixels=std::vector<uint8_t>(496*384*4);
 std::vector<uint8_t> bottom=std::vector<uint8_t>(496*384*4);
 std::vector<int16_t> audio;
 uint64_t frame=0;
 uint64_t clockFrames=0;
 std::time_t clockBase=std::time(nullptr);
 uint32_t fault=0;
 bool loaded=false;
};
static daytona2_context* active=nullptr;
unsigned daytona2_default_framebuffer(){return active?active->framebuffer.GetFBOID():0;}
std::time_t daytona2_clock(){return active?active->clockBase+(std::time_t)(active->clockFrames/60):std::time(nullptr);}
static std::string createError;
static std::string digestFile(const fs::path& path) {
 std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("Missing media: "+path.filename().string());
 CC_SHA256_CTX ctx;CC_SHA256_Init(&ctx);char bytes[65536];
 while(in){in.read(bytes,sizeof(bytes));if(in.gcount())CC_SHA256_Update(&ctx,bytes,(CC_LONG)in.gcount());}
 if(!in.eof())throw std::runtime_error("Could not read media");
 unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256_Final(digest,&ctx);
 std::ostringstream s;for(auto b:digest)s<<std::hex<<std::setw(2)<<std::setfill('0')<<(int)b;return s.str();
}
bool BeginFrameVideo(){return true;} void EndFrameVideo(){}
void SetAudioCallback(AudioCallbackFPtr,void*){} void SetAudioEnabled(bool){} void SetAudioType(Game::AudioTypes){}
Result OpenAudio(const Util::Config::Node&){return Result::OKAY;}void CloseAudio(){}
bool OutputAudio(unsigned n,const float* fl,const float* fr,const float* rl,const float* rr,bool flip){
 if(!active)return false;
 if(n>8192 || active->audio.size()+n*2>16384)throw std::runtime_error("PCM capacity exceeded");
 auto clamp=[](float f){return (int16_t)std::clamp((int)f,-32768,32767);};
 for(unsigned i=0;i<n;i++){auto l=clamp((fl[i]+rl[i])*0.5f),r=clamp((fr[i]+rr[i])*0.5f);active->audio.push_back(flip?r:l);active->audio.push_back(flip?l:r);}
 return false;
}
extern "C" {
void daytona2_native_fault(const char* message){throw std::runtime_error(message);}
#ifdef DAYTONA2_REFERENCE
void daytona2_reference_probe_marker(){}
#endif
const char* daytona2_error(const daytona2_context* c){return c?c->error.c_str():createError.c_str();}
uint32_t daytona2_fault_code(const daytona2_context* c){return c?c->fault:1;}
void daytona2_destroy(daytona2_context* c){
 if(!c||c!=active)return;
 if(c->gl)CGLSetCurrentContext(c->gl);
 if(c->loaded){CBlockFile nv;if(nv.Create(c->saves+"/daytona2.nv","Daytona2 NVRAM","Local original cabinet settings")==Result::OKAY)c->model->SaveNVRAM(&nv);}
 c->model.reset();c->r3.reset();c->r2.reset();c->aa.reset();c->framebuffer.Destroy();
 if(c->gl){CGLSetCurrentContext(nullptr);CGLDestroyContext(c->gl);}active=nullptr;delete c;
}
daytona2_context* daytona2_create(const char* assets,const char* saves){
 if(active){createError="A game session is already active";return nullptr;}
 if(!assets||!saves){createError="Missing asset or save directory";return nullptr;}
 auto c=new daytona2_context;active=c;
 try {
  if(digestFile(fs::path(assets)/"daytona2.zip")!=daytona2_zip_sha256 || digestFile(fs::path(assets)/"Games.xml")!=daytona2_xml_sha256)throw std::runtime_error("Game media does not match verified Revision A");
  fs::create_directories(saves);c->saves=saves;
#ifdef DAYTONA2_HAS_SETTINGS_SEED
  bool factory=false;
#ifdef DAYTONA2_REFERENCE
  factory=std::getenv("DAYTONA2_FACTORY_SETTINGS")!=nullptr;
#endif
  if(!factory&&!fs::exists(fs::path(saves)/"daytona2.nv")){
   auto seed=fs::path(assets)/"default.nv";
   if(digestFile(seed)!=daytona2_settings_sha256)throw std::runtime_error("Default cabinet settings identity mismatch");
   fs::copy_file(seed,fs::path(saves)/"daytona2.nv");
  }
#endif
  if(const char* epoch=std::getenv("DAYTONA2_RTC_EPOCH")){
   char* end=nullptr;auto value=std::strtoll(epoch,&end,10);
   if(!*epoch||*end||value<946684800||value>4102444800LL)throw std::runtime_error("Invalid cabinet clock epoch");
   c->clockBase=(std::time_t)value;
  }
  SetLogger(std::make_shared<CConsoleErrorLogger>());
  CGLPixelFormatAttribute attrs[]={kCGLPFAOpenGLProfile,(CGLPixelFormatAttribute)kCGLOGLPVersion_GL4_Core,kCGLPFAAccelerated,kCGLPFAColorSize,(CGLPixelFormatAttribute)24,kCGLPFADepthSize,(CGLPixelFormatAttribute)24,(CGLPixelFormatAttribute)0};
  CGLPixelFormatObj pf=nullptr;GLint count=0;
  if(CGLChoosePixelFormat(attrs,&pf,&count)!=kCGLNoError||!pf)throw std::runtime_error("OpenGL 4.1 pixel format unavailable");
  auto result=CGLCreateContext(pf,nullptr,&c->gl);CGLDestroyPixelFormat(pf);
  if(result!=kCGLNoError||!c->gl)throw std::runtime_error("Could not create graphics context");
  CGLSetCurrentContext(c->gl);glewExperimental=GL_TRUE;
  if(glewInit()!=GLEW_OK)throw std::runtime_error("Could not initialize graphics functions");
  while(glGetError()!=GL_NO_ERROR){}
  if(!c->framebuffer.Create(496,384))throw std::runtime_error("Could not create game framebuffer");
  glViewport(0,0,496,384);glEnable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE);
  glEnable(GL_SCISSOR_TEST);glScissor(2,2,492,380);
  c->inputs=std::make_unique<CInputs>(nullptr);
  c->model=std::make_unique<CModel3>(c->config);
  Game game;ROMSet roms;GameLoader loader((fs::path(assets)/"Games.xml").string());
  if(loader.Load(&game,&roms,(fs::path(assets)/"daytona2.zip").string())||game.name!="daytona2")throw std::runtime_error("Could not load verified Revision A");
  if(c->model->Init()!=Result::OKAY||c->model->LoadGame(game,roms)!=Result::OKAY)throw std::runtime_error("Could not initialize Model 3 hardware");
  c->model->AttachInputs(c->inputs.get());
  if(fs::exists(fs::path(saves)/"daytona2.nv")){CBlockFile nv;if(nv.Load(c->saves+"/daytona2.nv")!=Result::OKAY)throw std::runtime_error("Could not load cabinet settings");c->model->LoadNVRAM(&nv);}else c->model->ClearNVRAM();
  c->aa=std::make_unique<SuperAA>(1,CRTcolor::None);c->aa->Init(496,384);
  c->r2=std::make_unique<CRender2D>(c->config);c->r3=std::make_unique<New3D::CNew3D>(c->config,game.name);
  auto fbo=c->framebuffer.GetFBOID();
  if(c->r2->Init(0,0,496,384,496,384,fbo,UpscaleMode::Nearest)!=Result::OKAY||c->r3->Init(0,0,496,384,496,384,fbo)!=Result::OKAY)throw std::runtime_error("Could not initialize game renderer");
  c->model->AttachRenderers(c->r2.get(),c->r3.get(),c->aa.get());
  c->model->Reset();c->loaded=true;
  while(glGetError()!=GL_NO_ERROR){}
  return c;
 } catch(const std::exception& e){createError=e.what();daytona2_destroy(c);return nullptr;}
}
int daytona2_reset(daytona2_context* c){
 if(!c||c!=active||c->fault)return 0;
 try{c->model->Reset();c->inputs->gearShift4->value=0;c->frame=0;c->audio.clear();return 1;}
 catch(const std::exception& e){c->error=e.what();c->fault=1;return 0;}
}
int daytona2_step(daytona2_context* c,float steering,float accelerator,float brake,uint32_t buttons){
 if(!c||c!=active||c->fault)return 0;
 uint32_t gear=buttons&1984u;
 uint32_t allowed=2047u;
#ifdef DAYTONA2_REFERENCE
 allowed|=(1u<<16)|(1u<<17);
#endif
 if(!std::isfinite(steering)||!std::isfinite(accelerator)||!std::isfinite(brake)||std::abs(steering)>1||accelerator<0||accelerator>1||brake<0||brake>1||(buttons&~allowed)||(gear&&(gear&(gear-1)))){c->error="Invalid driving input";return 0;}
 try{
  CGLSetCurrentContext(c->gl);auto& i=*c->inputs;
  i.steering->value=(uint16_t)std::lround((steering+1.f)*127.5f);
  i.accelerator->value=(uint16_t)std::lround(accelerator*255.f);i.brake->value=(uint16_t)std::lround(brake*255.f);
  i.coin[0]->value=(buttons&1)?1:0;i.start[0]->value=(buttons&2)?1:0;
  for(unsigned v=0;v<4;v++)i.vr[v]->value=(buttons&(4<<v))?1:0;
  if(gear)for(unsigned g=0;g<5;g++)if(gear&(64<<g))i.gearShift4->value=g;
#ifdef DAYTONA2_REFERENCE
  i.test[0]->value=(buttons>>16)&1;i.service[0]->value=(buttons>>17)&1;
#endif
  c->audio.clear();c->model->RunFrame();
  glBindFramebuffer(GL_READ_FRAMEBUFFER,c->framebuffer.GetFBOID());
  glReadBuffer(GL_COLOR_ATTACHMENT0);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(0,0,496,384,GL_RGBA,GL_UNSIGNED_BYTE,c->bottom.data());
  auto glError=glGetError();if(glError!=GL_NO_ERROR)throw std::runtime_error("Graphics readback failed: "+std::to_string(glError));
  for(unsigned y=0;y<384;y++)std::copy_n(c->bottom.data()+(383-y)*496*4,496*4,c->pixels.data()+y*496*4);
  for(size_t n=3;n<c->pixels.size();n+=4)c->pixels[n]=255;
  ++c->frame;++c->clockFrames;return 1;
 }catch(const std::exception& e){c->error=e.what();c->fault=1;return 0;}
}
const uint8_t* daytona2_pixels(const daytona2_context* c){return c?c->pixels.data():nullptr;}
const int16_t* daytona2_audio(const daytona2_context* c){return c?c->audio.data():nullptr;}
int daytona2_audio_count(const daytona2_context* c){return c?(int)c->audio.size()/2:0;}
int daytona2_width(const daytona2_context*){return 496;}int daytona2_height(const daytona2_context*){return 384;}
double daytona2_frame_rate(const daytona2_context*){return 60.;}int daytona2_audio_sample_rate(const daytona2_context*){return 44100;}
uint64_t daytona2_frame_number(const daytona2_context* c){return c?c->frame:0;}
#ifdef DAYTONA2_REFERENCE
uint32_t daytona2_diagnostic_read32(daytona2_context* c,uint32_t address){return c->model->Read32(address);}
uint32_t daytona2_diagnostic_pc(daytona2_context*){return ppc_get_pc();}
uint32_t daytona2_diagnostic_gpr(daytona2_context*,unsigned n){return ppc_get_gpr(n);}
void daytona2_diagnostic_save_state(daytona2_context* c,const char* path){CBlockFile file;if(file.Create(path,"Daytona2 lab state","Original reference only")==Result::OKAY)c->model->SaveState(&file);}
#endif
}
