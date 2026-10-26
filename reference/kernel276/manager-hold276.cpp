
#include <libcamera/libcamera.h>
#include <iostream>
#include <string>
int main()
{
 libcamera::CameraManager manager;
 int ret=manager.start();
 if(ret)return 1;
 std::cout<<"{\"event\":\"ready\",\"cameras\":"<<manager.cameras().size()<<"}"<<std::endl;
 std::string command;
 if(!std::getline(std::cin,command) || command!="stop")return 2;
 manager.stop();
 std::cout<<"{\"event\":\"stopped\"}"<<std::endl;
 return 0;
}
