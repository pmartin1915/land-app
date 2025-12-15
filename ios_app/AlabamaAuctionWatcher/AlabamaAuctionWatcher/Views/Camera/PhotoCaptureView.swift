import SwiftUI
import UIKit
import CoreLocation

struct PhotoCaptureView: View {
    let property: Property
    @Environment(\.presentationMode) var presentationMode
    @State private var showingImagePicker = false
    @State private var capturedImage: UIImage?
    @State private var caption = ""
    @State private var currentLocation: CLLocationCoordinate2D?

    private let locationManager = CLLocationManager()

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if let image = capturedImage {
                    capturedImageView(image)
                } else {
                    cameraPromptView
                }
            }
            .padding()
            .navigationTitle("Field Photos")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        presentationMode.wrappedValue.dismiss()
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        savePhoto()
                    }
                    .disabled(capturedImage == nil)
                }
            }
            .sheet(isPresented: $showingImagePicker) {
                ImagePicker(image: $capturedImage, sourceType: .camera)
            }
            .onAppear {
                requestLocationPermission()
            }
        }
    }

    private var cameraPromptView: some View {
        VStack(spacing: 30) {
            Image(systemName: "camera.fill")
                .font(.system(size: 60))
                .foregroundColor(.blue)

            VStack(spacing: 10) {
                Text("Take Field Verification Photo")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Document the property condition and features for your records")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            Button(action: { showingImagePicker = true }) {
                Label("Open Camera", systemImage: "camera")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .cornerRadius(12)
            }

            Spacer()
        }
    }

    private func capturedImageView(_ image: UIImage) -> some View {
        VStack(spacing: 20) {
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(maxHeight: 300)
                .cornerRadius(12)

            VStack(alignment: .leading, spacing: 8) {
                Text("Add Caption")
                    .font(.headline)

                TextField("Describe what you see...", text: $caption, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3...6)
            }

            if let location = currentLocation {
                HStack {
                    Image(systemName: "location.fill")
                        .foregroundColor(.green)
                    Text("Location captured: \(location.latitude, specifier: "%.6f"), \(location.longitude, specifier: "%.6f")")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                }
            }

            Button(action: { showingImagePicker = true }) {
                Label("Retake Photo", systemImage: "camera.rotate")
                    .foregroundColor(.blue)
            }

            Spacer()
        }
    }

    private func requestLocationPermission() {
        let manager = CLLocationManager()
        manager.requestWhenInUseAuthorization()

        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways {
            manager.requestLocation()
            currentLocation = manager.location?.coordinate
        }
    }

    private func savePhoto() {
        guard let image = capturedImage else { return }

        let context = PersistenceController.shared.container.viewContext
        let photoEntity = PropertyPhoto(context: context)

        photoEntity.photoId = UUID()
        photoEntity.fileName = "\(photoEntity.photoId?.uuidString ?? "unknown").jpg"
        photoEntity.caption = caption.isEmpty ? nil : caption
        photoEntity.createdAt = Date()
        photoEntity.property = property

        if let location = currentLocation {
            photoEntity.latitude = location.latitude
            photoEntity.longitude = location.longitude
        }

        // In a real app, you'd save the image to the Documents directory or CloudKit
        // and store just the filename in Core Data

        do {
            try context.save()
            presentationMode.wrappedValue.dismiss()
        } catch {
            print("Error saving photo: \(error)")
        }
    }
}

struct ImagePicker: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    let sourceType: UIImagePickerController.SourceType

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker

        init(_ parent: ImagePicker) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let uiImage = info[.originalImage] as? UIImage {
                parent.image = uiImage
            }

            picker.dismiss(animated: true)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}

struct PhotoGridView: View {
    let photos: [PropertyPhoto]

    private let columns = Array(repeating: GridItem(.flexible()), count: 3)

    var body: some View {
        LazyVGrid(columns: columns, spacing: 8) {
            ForEach(photos, id: \.photoId) { photo in
                PhotoThumbnailView(photo: photo)
            }
        }
    }
}

struct PhotoThumbnailView: View {
    let photo: PropertyPhoto

    var body: some View {
        VStack {
            // In a real app, you'd load the actual image from storage
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .aspectRatio(1, contentMode: .fit)
                .overlay(
                    Image(systemName: "photo")
                        .font(.title2)
                        .foregroundColor(.gray)
                )
                .cornerRadius(8)

            if let caption = photo.caption, !caption.isEmpty {
                Text(caption)
                    .font(.caption2)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
            }

            if let date = photo.createdAt {
                Text(date.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    let context = PersistenceController.preview.container.viewContext
    let property = Property(context: context)
    property.parcelId = "SAMPLE001"

    return PhotoCaptureView(property: property)
}