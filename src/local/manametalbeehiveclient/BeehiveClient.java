package local.manametalbeehiveclient;

import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.SidedProxy;
import cpw.mods.fml.common.event.FMLInitializationEvent;

@Mod(modid="manametalbeehiveclient", name="魔法金属蜂箱按钮", version="1.0.0",
        acceptedMinecraftVersions="[1.7.10]", acceptableRemoteVersions="*",
        dependencies="required-after:manametalmod")
public final class BeehiveClient {
    @SidedProxy(clientSide="local.manametalbeehiveclient.ClientProxy",
            serverSide="local.manametalbeehiveclient.CommonProxy")
    public static CommonProxy proxy;

    @Mod.EventHandler public void init(FMLInitializationEvent event) { proxy.init(); }
}
