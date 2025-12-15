import SwiftUI

struct FilterView: View {
    @ObservedObject var filterOptions: FilterOptions
    @Environment(\.presentationMode) var presentationMode

    var body: some View {
        NavigationView {
            Form {
                Section("Price Range") {
                    VStack {
                        HStack {
                            Text("$\(Int(filterOptions.priceRange.lowerBound))")
                            Spacer()
                            Text("$\(Int(filterOptions.priceRange.upperBound))")
                        }
                        .font(.caption)
                        .foregroundColor(.secondary)

                        RangeSlider(
                            range: $filterOptions.priceRange,
                            bounds: 0...100000,
                            step: 1000
                        )
                    }
                }

                Section("Acreage Range") {
                    VStack {
                        HStack {
                            Text("\(filterOptions.acreageRange.lowerBound, specifier: "%.1f")")
                            Spacer()
                            Text("\(filterOptions.acreageRange.upperBound, specifier: "%.1f")")
                        }
                        .font(.caption)
                        .foregroundColor(.secondary)

                        RangeSlider(
                            range: $filterOptions.acreageRange,
                            bounds: 0...20,
                            step: 0.1
                        )
                    }
                }

                Section("Water Features") {
                    Toggle("Properties with water features only", isOn: $filterOptions.waterFeaturesOnly)
                }

                Section("County") {
                    Picker("County", selection: $filterOptions.selectedCounty) {
                        ForEach(FilterOptions.allCounties, id: \.self) { county in
                            Text(county).tag(county as String?)
                        }
                    }
                    .pickerStyle(.menu)
                }

                Section("Investment Score") {
                    VStack {
                        HStack {
                            Text("Minimum Score: \(filterOptions.minimumInvestmentScore, specifier: "%.1f")")
                            Spacer()
                        }

                        Slider(
                            value: $filterOptions.minimumInvestmentScore,
                            in: 0...100,
                            step: 1
                        )
                    }
                }

                Section {
                    Button("Reset Filters") {
                        resetFilters()
                    }
                    .foregroundColor(.red)
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        presentationMode.wrappedValue.dismiss()
                    }
                }
            }
        }
    }

    private func resetFilters() {
        filterOptions.priceRange = 0...50000
        filterOptions.acreageRange = 0...10
        filterOptions.waterFeaturesOnly = false
        filterOptions.selectedCounty = "All"
        filterOptions.minimumInvestmentScore = 0
    }
}

struct RangeSlider: UIViewRepresentable {
    @Binding var range: ClosedRange<Double>
    let bounds: ClosedRange<Double>
    let step: Double

    func makeUIView(context: Context) -> UIRangeSlider {
        let slider = UIRangeSlider()
        slider.minimumValue = Float(bounds.lowerBound)
        slider.maximumValue = Float(bounds.upperBound)
        slider.lowerValue = Float(range.lowerBound)
        slider.upperValue = Float(range.upperBound)
        slider.addTarget(context.coordinator, action: #selector(Coordinator.valueChanged), for: .valueChanged)
        return slider
    }

    func updateUIView(_ uiView: UIRangeSlider, context: Context) {
        uiView.lowerValue = Float(range.lowerBound)
        uiView.upperValue = Float(range.upperBound)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject {
        let parent: RangeSlider

        init(_ parent: RangeSlider) {
            self.parent = parent
        }

        @objc func valueChanged(_ sender: UIRangeSlider) {
            let lower = Double(sender.lowerValue)
            let upper = Double(sender.upperValue)

            let steppedLower = (lower / parent.step).rounded() * parent.step
            let steppedUpper = (upper / parent.step).rounded() * parent.step

            parent.range = steppedLower...steppedUpper
        }
    }
}

class UIRangeSlider: UIControl {
    var minimumValue: Float = 0.0
    var maximumValue: Float = 1.0
    var lowerValue: Float = 0.2
    var upperValue: Float = 0.8

    private let trackLayer = CALayer()
    private let lowerThumbLayer = CALayer()
    private let upperThumbLayer = CALayer()

    override init(frame: CGRect) {
        super.init(frame: frame)
        setup()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setup()
    }

    private func setup() {
        trackLayer.backgroundColor = UIColor.systemGray4.cgColor
        layer.addSublayer(trackLayer)

        lowerThumbLayer.backgroundColor = UIColor.systemBlue.cgColor
        lowerThumbLayer.cornerRadius = 12
        layer.addSublayer(lowerThumbLayer)

        upperThumbLayer.backgroundColor = UIColor.systemBlue.cgColor
        upperThumbLayer.cornerRadius = 12
        layer.addSublayer(upperThumbLayer)
    }

    override func layoutSubviews() {
        super.layoutSubviews()

        let trackHeight: CGFloat = 4
        trackLayer.frame = CGRect(x: 12, y: (bounds.height - trackHeight) / 2, width: bounds.width - 24, height: trackHeight)
        trackLayer.cornerRadius = trackHeight / 2

        let thumbSize: CGFloat = 24
        let trackWidth = trackLayer.bounds.width
        let lowerPosition = CGFloat((lowerValue - minimumValue) / (maximumValue - minimumValue)) * trackWidth
        let upperPosition = CGFloat((upperValue - minimumValue) / (maximumValue - minimumValue)) * trackWidth

        lowerThumbLayer.frame = CGRect(x: trackLayer.frame.minX + lowerPosition - thumbSize/2, y: (bounds.height - thumbSize) / 2, width: thumbSize, height: thumbSize)
        upperThumbLayer.frame = CGRect(x: trackLayer.frame.minX + upperPosition - thumbSize/2, y: (bounds.height - thumbSize) / 2, width: thumbSize, height: thumbSize)
    }

    override func beginTracking(_ touch: UITouch, with event: UIEvent?) -> Bool {
        let location = touch.location(in: self)

        if lowerThumbLayer.frame.contains(location) || upperThumbLayer.frame.contains(location) {
            return true
        }

        return false
    }

    override func continueTracking(_ touch: UITouch, with event: UIEvent?) -> Bool {
        let location = touch.location(in: self)
        let trackWidth = trackLayer.bounds.width
        let relativePosition = Float((location.x - trackLayer.frame.minX) / trackWidth)
        let value = minimumValue + relativePosition * (maximumValue - minimumValue)

        let lowerDistance = abs(value - lowerValue)
        let upperDistance = abs(value - upperValue)

        if lowerDistance < upperDistance {
            lowerValue = max(minimumValue, min(value, upperValue))
        } else {
            upperValue = max(lowerValue, min(value, maximumValue))
        }

        setNeedsLayout()
        sendActions(for: .valueChanged)
        return true
    }
}

#Preview {
    FilterView(filterOptions: FilterOptions())
}