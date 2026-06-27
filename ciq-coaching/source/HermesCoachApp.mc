using Toybox.Application;
using Toybox.WatchUi;

class HermesCoachApp extends Application.AppBase {

    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() {
        return [ new HermesCoachView() ];
    }
}
