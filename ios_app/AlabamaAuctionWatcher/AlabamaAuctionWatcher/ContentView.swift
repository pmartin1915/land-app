import SwiftUI
import CoreData

struct ContentView: View {
    @Environment(\.managedObjectContext) private var viewContext

    var body: some View {
        TabView {
            PropertyListView()
                .tabItem {
                    Image(systemName: "house.fill")
                    Text("Properties")
                }

            MapView()
                .tabItem {
                    Image(systemName: "map.fill")
                    Text("Map")
                }

            FavoritesView()
                .tabItem {
                    Image(systemName: "heart.fill")
                    Text("Favorites")
                }

            SettingsView()
                .tabItem {
                    Image(systemName: "gear")
                    Text("Settings")
                }
        }
        .accentColor(.blue)
    }
}

struct FavoritesView: View {
    var body: some View {
        NavigationView {
            Text("Favorites")
                .navigationTitle("Favorites")
        }
    }
}

struct SettingsView: View {
    var body: some View {
        NavigationView {
            Text("Settings")
                .navigationTitle("Settings")
        }
    }
}

#Preview {
    ContentView().environment(\.managedObjectContext, PersistenceController.preview.container.viewContext)
}