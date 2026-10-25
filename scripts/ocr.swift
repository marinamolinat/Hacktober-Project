import Foundation
import Vision

// Recognize source text only. Event interpretation belongs to the ingestion layer.
var output: [String: String] = [:]
for imagePath in CommandLine.arguments.dropFirst() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-US"]
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: imagePath), options: [:])
    do {
        try handler.perform([request])
        let lines = (request.results ?? []).compactMap { observation in
            observation.topCandidates(1).first?.string.trimmingCharacters(in: .whitespacesAndNewlines)
        }.filter { !$0.isEmpty }
        output[imagePath] = lines.joined(separator: "\n")
    } catch {
        FileHandle.standardError.write(Data("OCR failed for \(imagePath): \(error.localizedDescription)\n".utf8))
        exit(1)
    }
}
let encoded = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(encoded)
FileHandle.standardOutput.write(Data("\n".utf8))
