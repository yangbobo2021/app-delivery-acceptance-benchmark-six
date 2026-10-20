/** Non-business JVM probe: never calls the batch entry or reads/writes business data. */
public class CoverageProbe {
    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("initialize")) {
            Class.forName("benchmark.BatchReport");
        }
    }
}
