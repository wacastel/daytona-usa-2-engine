import AppKit

// Original geometric artwork; no game imagery, logos or supplied ROM data.
guard CommandLine.arguments.count == 2 else { fatalError("Expected output iconset directory") }
let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

func color(_ hex: UInt32, _ alpha: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 255) / 255,
            green: CGFloat((hex >> 8) & 255) / 255,
            blue: CGFloat(hex & 255) / 255, alpha: alpha)
}
func polygon(_ points: [NSPoint], _ fill: NSColor) {
    let path = NSBezierPath(); path.move(to: points[0])
    for point in points.dropFirst() { path.line(to: point) }
    path.close(); fill.setFill(); path.fill()
}
func draw(size: Int) -> Data {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
                                 bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                 isPlanar: false, colorSpaceName: .deviceRGB,
                                 bytesPerRow: size * 4, bitsPerPixel: 32)!
    let context = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = context
    context.cgContext.scaleBy(x: CGFloat(size) / 1024, y: CGFloat(size) / 1024)
    let base = NSBezierPath(roundedRect: NSRect(x: 48, y: 48, width: 928, height: 928), xRadius: 204, yRadius: 204)
    let shadow = NSShadow(); shadow.shadowColor = color(0x021129, 0.35)
    shadow.shadowBlurRadius = 24; shadow.shadowOffset = NSSize(width: 0, height: -12)
    shadow.set(); color(0x031327).setFill(); base.fill()
    NSShadow().set(); base.addClip()
    NSGradient(starting: color(0x134886), ending: color(0x041529))!.draw(in: base, angle: -75)
    // Banking track ribbons and two fine lane markings create forward motion.
    polygon([NSPoint(x: -80, y: 90), NSPoint(x: 710, y: 976), NSPoint(x: 1070, y: 976), NSPoint(x: 165, y: -70)], color(0x147BE0))
    polygon([NSPoint(x: 117, y: 48), NSPoint(x: 915, y: 976), NSPoint(x: 946, y: 976), NSPoint(x: 151, y: 48)], color(0x7FEAFF, 0.80))
    polygon([NSPoint(x: 266, y: 48), NSPoint(x: 1064, y: 976), NSPoint(x: 1095, y: 976), NSPoint(x: 300, y: 48)], color(0x052954))
    polygon([NSPoint(x: -100, y: 398), NSPoint(x: 1024, y: 672), NSPoint(x: 1024, y: 828), NSPoint(x: -100, y: 554)], color(0xF03F49))
    polygon([NSPoint(x: -100, y: 554), NSPoint(x: 1024, y: 828), NSPoint(x: 1024, y: 842), NSPoint(x: -100, y: 568)], color(0xFF9A85, 0.80))
    // Original checker detail, small enough to read as a racing accent.
    context.cgContext.saveGState()
    context.cgContext.translateBy(x: 652, y: 147); context.cgContext.rotate(by: -0.20)
    for y in 0..<3 { for x in 0..<5 {
        ((x + y) % 2 == 0 ? color(0xE8F5FF) : color(0x102038)).setFill()
        NSBezierPath(rect: NSRect(x: x * 42, y: y * 42, width: 42, height: 42)).fill()
    } }
    context.cgContext.restoreGState()
    let font = NSFont(name: "AvenirNextCondensed-HeavyItalic", size: 640) ?? NSFont.systemFont(ofSize: 640, weight: .black)
    let number = "2" as NSString
    let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: color(0xFAFDFF), .kern: -12]
    let bounds = number.size(withAttributes: attrs)
    let numberShadow = NSShadow(); numberShadow.shadowColor = color(0x00102A, 0.65)
    numberShadow.shadowBlurRadius = 9; numberShadow.shadowOffset = NSSize(width: 7, height: -14)
    numberShadow.set()
    number.draw(at: NSPoint(x: (1024 - bounds.width) / 2 - 25, y: 198), withAttributes: attrs)
    NSShadow().set()
    let edge = NSBezierPath(roundedRect: NSRect(x: 51, y: 51, width: 922, height: 922), xRadius: 201, yRadius: 201)
    edge.lineWidth = 6; color(0xD2F0FF, 0.18).setStroke(); edge.stroke()
    context.flushGraphics(); NSGraphicsContext.restoreGraphicsState()
    return bitmap.representation(using: .png, properties: [:])!
}
for points in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let suffix = scale == 1 ? "" : "@2x"
        try draw(size: points * scale).write(to: directory.appendingPathComponent("icon_\(points)x\(points)\(suffix).png"))
    }
}
