import ReplayKit
import UIKit

/// Thin wrapper around RPSystemBroadcastPickerView — the system control that
/// starts/stops a whole-screen broadcast into our Broadcast Upload Extension.
/// Apple renders this control itself (icon + tap target); apps cannot
/// customize its internals or trigger it without a direct user tap.
final class BroadcastPickerView: UIView {
    private let picker = RPSystemBroadcastPickerView()

    override init(frame: CGRect) {
        super.init(frame: frame)
        // Must match the Broadcast Upload Extension target's bundle identifier,
        // set in Xcode under the extension's General settings.
        picker.preferredExtension = "com.mobilerecorder.app.BroadcastExtension"
        picker.showsMicrophoneButton = true
        picker.translatesAutoresizingMaskIntoConstraints = false
        addSubview(picker)
        NSLayoutConstraint.activate([
            picker.leadingAnchor.constraint(equalTo: leadingAnchor),
            picker.trailingAnchor.constraint(equalTo: trailingAnchor),
            picker.topAnchor.constraint(equalTo: topAnchor),
            picker.bottomAnchor.constraint(equalTo: bottomAnchor),
        ])
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}
