// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CyberAgent",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "CyberAgent", targets: ["CyberAgent"]),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "CyberAgent",
            path: "CyberAgent",
            resources: [.process("Assets.xcassets")]
        ),
        .testTarget(
            name: "CyberAgentTests",
            dependencies: ["CyberAgent"],
            path: "../CyberAgentTests"
        ),
    ]
)
