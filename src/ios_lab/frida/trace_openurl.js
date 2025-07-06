// Hook UIApplication openURL on jailbroken device
if (ObjC.available) {
    var UIApplication = ObjC.classes.UIApplication;
    var sharedApp = UIApplication.sharedApplication();

    Interceptor.attach(sharedApp.openURL_.implementation, {
        onEnter: function(args) {
            var url = new ObjC.Object(args[2]);
            console.log("[*] openURL called with: " + url.toString());
        }
    });
}
