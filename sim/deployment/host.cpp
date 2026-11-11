#include <fstream>
#include "actor.hpp"

int main(int argc, char **argv) {
    if (argc != 3) return 1;
    std::ifstream inputs(argv[1], std::ios::binary);
    std::ofstream outputs(argv[2], std::ios::binary);
    if (!inputs || !outputs) return 1;
    static_assert(sizeof(float) == 4, "parity files use float32");
    actor::Workspace work{};
    float obs[actor::kInputs], action[actor::kOutputs];
    while (inputs.read(reinterpret_cast<char *>(obs), sizeof(obs))) {
        actor::predict(obs, action, work);
        outputs.write(reinterpret_cast<const char *>(action), sizeof(action));
    }
    outputs.close();
    return inputs.eof() && inputs.gcount() == 0 && outputs ? 0 : 1;
}
