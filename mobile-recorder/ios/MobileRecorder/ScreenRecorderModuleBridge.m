#import <React/RCTBridgeModule.h>

// Bridges the Swift ScreenRecorderModule class into RN's module registry.
// RCT_EXTERN_MODULE looks the class up by name at runtime, so no Swift
// import is needed here.
@interface RCT_EXTERN_MODULE(ScreenRecorderModule, RCTEventEmitter)

RCT_EXTERN_METHOD(requestPermissions
                  : (RCTPromiseResolveBlock)resolve rejecter
                  : (RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(startRecording
                  : (RCTPromiseResolveBlock)resolve rejecter
                  : (RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(stopRecording
                  : (RCTPromiseResolveBlock)resolve rejecter
                  : (RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getLatestBroadcastFile
                  : (RCTPromiseResolveBlock)resolve rejecter
                  : (RCTPromiseRejectBlock)reject)

@end
