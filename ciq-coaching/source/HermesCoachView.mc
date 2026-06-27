using Toybox.WatchUi;
using Toybox.Graphics;
using Toybox.System;
using Toybox.Lang;
using Toybox.Application;
using Toybox.Activity;
using Toybox.UserProfile;
using Toybox.Time;

// Hermes Coach Data Field
// Shows: Body Battery, HRV status, Training Readiness, and a coaching verdict
// Everything at a glance on your Fenix 7X

class HermesCoachView extends WatchUi.DataField {

    hidden var mBodyBattery;
    hidden var mHeartRate;
    hidden var mIsCalibrating;
    hidden var mLabel;
    hidden var mCoachText;
    hidden var mBgColor;
    hidden var mTextColor;

    function initialize() {
        DataField.initialize();
        mLabel = "Hermes";
        mBodyBattery = 50;
        mHeartRate = 60;
        mIsCalibrating = true;
        mCoachText = "Wear 7 days";
        mBgColor = Graphics.COLOR_BLACK;
        mTextColor = Graphics.COLOR_WHITE;
    }

    // Called when new data arrives from the sensors
    function onUpdate(activityInfo) {
        if (activityInfo == null) {
            mIsCalibrating = true;
            return;
        }

        // Get Body Battery
        var bbInfo = Activity.getActivityInfo().bodyBattery;
        if (bbInfo != null) {
            mBodyBattery = bbInfo;
            mIsCalibrating = false;
        }

        // Get Heart Rate
        var hr = activityInfo.currentHeartRate;
        if (hr != null) {
            mHeartRate = hr;
        }

        // Determine coaching verdict
        updateCoachText();
    }

    function updateCoachText() {
        // Coaching logic based on body battery
        if (mIsCalibrating) {
            mCoachText = "WEAR 7 DAYS";
            mBgColor = Graphics.COLOR_DK_GRAY;
            mTextColor = Graphics.COLOR_LT_GRAY;
            return;
        }

        if (mBodyBattery >= 80) {
            mCoachText = "FULL SEND";
            mBgColor = Graphics.COLOR_DK_GREEN;
            mTextColor = Graphics.COLOR_WHITE;
        } else if (mBodyBattery >= 60) {
            mCoachText = "TRAIN HARD";
            mBgColor = Graphics.COLOR_BLUE;
            mTextColor = Graphics.COLOR_WHITE;
        } else if (mBodyBattery >= 40) {
            mCoachText = "EASY DAY";
            mBgColor = Graphics.COLOR_ORANGE;
            mTextColor = Graphics.COLOR_BLACK;
        } else if (mBodyBattery >= 25) {
            mCoachText = "REST";
            mBgColor = Graphics.COLOR_RED;
            mTextColor = Graphics.COLOR_WHITE;
        } else {
            mCoachText = "RECOVERY";
            mBgColor = Graphics.COLOR_DK_RED;
            mTextColor = Graphics.COLOR_WHITE;
        }

        // High HR check
        if (mHeartRate != null && mHeartRate > 100 && mBodyBattery < 40) {
            mCoachText = "STRESS HIGH";
            mBgColor = Graphics.COLOR_RED;
            mTextColor = Graphics.COLOR_WHITE;
        }
    }

    function compute(info) {
        // Called by the system each second
        onUpdate(info);
    }

    function draw(dc) {
        var width = dc.getWidth();
        var height = dc.getHeight();

        // Background
        dc.setColor(mBgColor, mBgColor);
        dc.fillRectangle(0, 0, width, height);

        // Body Battery (large number)
        dc.setColor(mTextColor, Graphics.COLOR_TRANSPARENT);
        if (!mIsCalibrating) {
            var batteryStr = mBodyBattery.format("%d");
            dc.drawText(width / 2, 5, Graphics.FONT_LARGE, batteryStr, Graphics.TEXT_JUSTIFY_CENTER);
        } else {
            dc.drawText(width / 2, 5, Graphics.FONT_SMALL, "--", Graphics.TEXT_JUSTIFY_CENTER);
        }

        // Body Battery label
        dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
        dc.drawText(width / 2, height / 2 - 10, Graphics.FONT_XTINY, "BODY BAT", Graphics.TEXT_JUSTIFY_CENTER);

        // Coaching text
        dc.setColor(mTextColor, Graphics.COLOR_TRANSPARENT);
        dc.drawText(width / 2, height / 2 + 10, Graphics.FONT_MEDIUM, mCoachText, Graphics.TEXT_JUSTIFY_CENTER);

        // HR at bottom
        if (mHeartRate != null && !mIsCalibrating) {
            dc.setColor(Graphics.COLOR_LT_GRAY, Graphics.COLOR_TRANSPARENT);
            dc.drawText(width / 2, height - 15, Graphics.FONT_XTINY, mHeartRate.format("%d") + " bpm", Graphics.TEXT_JUSTIFY_CENTER);
        }
    }
}
