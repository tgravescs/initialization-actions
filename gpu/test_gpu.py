from absl.testing import absltest
from absl.testing import parameterized

from integration_tests.dataproc_test_case import DataprocTestCase


class NvidiaGpuDriverTestCase(DataprocTestCase):
  COMPONENT = "gpu"
  INIT_ACTIONS = ["gpu/install_gpu_driver.sh"]
  MIG_STARTUP_SCRIPTS = ["gpu/mig.sh"]
  GPU_V100 = "type=nvidia-tesla-v100"
  GPU_A100 = "type=nvidia-tesla-a100"

  def verify_instance(self, name):
    self.assert_instance_command(name, "nvidia-smi")

  def verify_instance_gpu_agent(self, name):
    self.assert_instance_command(
        name, "systemctl status gpu-utilization-agent.service")

  def verify_instance_cudnn(self, name):
    self.assert_instance_command(
        name, "sudo ldconfig -p | grep -q libcudnn" )

  @parameterized.parameters(
      ("SINGLE", ["m"], GPU_V100, None, None),
      ("STANDARD", ["m"], GPU_V100, None, None),
      ("STANDARD", ["m", "w-0", "w-1"], GPU_V100, GPU_V100, "NVIDIA"),
      ("STANDARD", ["w-0", "w-1"], None, GPU_V100, "NVIDIA"),
  )
  def test_install_gpu_default_agent(self, configuration, machine_suffixes,
                                     master_accelerator, worker_accelerator,
                                     driver_provider):
    metadata = None
    if driver_provider is not None:
      metadata = "gpu-driver-provider={}".format(driver_provider)
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=metadata,
        timeout_in_minutes=30)
    for machine_suffix in machine_suffixes:
      self.verify_instance("{}-{}".format(self.getClusterName(),
                                          machine_suffix))

  @parameterized.parameters(
      ("STANDARD", ["w-0", "w-1"], None, GPU_V100, None),
      ("STANDARD", ["m"], GPU_V100, None, "NVIDIA"),
      ("STANDARD", ["m", "w-0", "w-1"], GPU_V100, GPU_V100, "NVIDIA"),
  )
  def test_install_gpu_without_agent(self, configuration, machine_suffixes,
                                     master_accelerator, worker_accelerator,
                                     driver_provider):
    metadata = "install-gpu-agent=false"
    if driver_provider is not None:
      metadata += ",gpu-driver-provider={}".format(driver_provider)
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=metadata,
        timeout_in_minutes=30)
    for machine_suffix in machine_suffixes:
      self.verify_instance("{}-{}".format(self.getClusterName(),
                                          machine_suffix))

  @parameterized.parameters(
      ("STANDARD", ["m", "w-0", "w-1"], GPU_V100, GPU_V100, None),
      ("STANDARD", ["w-0", "w-1"], None, GPU_V100, "NVIDIA"),
      ("STANDARD", ["m"], GPU_V100, None, "NVIDIA"),
  )
  def test_install_gpu_with_agent(self, configuration, machine_suffixes,
                                  master_accelerator, worker_accelerator,
                                  driver_provider):
    metadata = "install-gpu-agent=true"
    if driver_provider is not None:
      metadata += ",gpu-driver-provider={}".format(driver_provider)
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=metadata,
        timeout_in_minutes=30,
        scopes="https://www.googleapis.com/auth/monitoring.write")
    for machine_suffix in machine_suffixes:
      self.verify_instance("{}-{}".format(self.getClusterName(),
                                          machine_suffix))
      self.verify_instance_gpu_agent("{}-{}".format(self.getClusterName(),
                                                    machine_suffix))

  @parameterized.parameters(
      ("SINGLE", ["m"], GPU_V100, None, "10.1"),
      ("STANDARD", ["m"], GPU_V100, None, "10.2"),
      ("STANDARD", ["m", "w-0", "w-1"], GPU_V100, GPU_V100, "11.0"),
      ("STANDARD", ["w-0", "w-1"], None, GPU_V100, "11.1"),
      ("STANDARD", ["w-0", "w-1"], None, GPU_V100, "11.2"),
  )
  def test_install_gpu_cuda_nvidia(self, configuration, machine_suffixes,
                                   master_accelerator, worker_accelerator,
                                   cuda_version):
    metadata = "gpu-driver-provider=NVIDIA,cuda-version={}".format(cuda_version)
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=metadata,
        timeout_in_minutes=30)
    for machine_suffix in machine_suffixes:
      self.verify_instance("{}-{}".format(self.getClusterName(),
                                          machine_suffix))

  @parameterized.parameters(
      ("STANDARD", ["m", "w-0", "w-1"], GPU_V100, GPU_V100, "NVIDIA", "8.1.1.33"),
  )
  def test_install_gpu_with_cudnn(self, configuration, machine_suffixes,
                                  master_accelerator, worker_accelerator,
                                  driver_provider, cudnn_version):
    metadata = "cudnn-version={}".format(cudnn_version)
    if driver_provider is not None:
      metadata += ",gpu-driver-provider={}".format(driver_provider)
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=metadata,
        timeout_in_minutes=30,
        scopes="https://www.googleapis.com/auth/monitoring.write")
    for machine_suffix in machine_suffixes:
      self.verify_instance_cudnn("{}-{}".format(self.getClusterName(),
                                                machine_suffix))

  @parameterized.parameters(
      ("SINGLE", GPU_V100, None, None),
      ("STANDARD", GPU_V100, GPU_V100, "NVIDIA")
  )
  def test_gpu_allocation(self, configuration, master_accelerator,
                          worker_accelerator, driver_provider):
    if configuration == "SINGLE" and self.getImageOs() == "rocky":
      self.skipTest("Test hangs on single-node clsuter with Rocky Linux-based images")
      
    metadata = None
    if driver_provider is not None:
      metadata = "gpu-driver-provider={}".format(driver_provider)

    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        metadata=metadata,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        timeout_in_minutes=30)

    self.assert_dataproc_job(
        self.getClusterName(),
        "spark",
        "--jars=file:///usr/lib/spark/examples/jars/spark-examples.jar --class=org.apache.spark.examples.ml.JavaIndexToStringExample --properties=spark.driver.resource.gpu.amount=1,spark.driver.resource.gpu.discoveryScript=/usr/lib/spark/scripts/gpu/getGpusResources.sh,spark.executor.resource.gpu.amount=1,spark.executor.resource.gpu.discoveryScript=/usr/lib/spark/scripts/gpu/getGpusResources.sh"
    )

  @parameterized.parameters(
      ("STANDARD", ["m", "w-0", "w-1"], GPU_A100, GPU_A100, "NVIDIA"),
  )
  def test_install_gpu_with_mig(self, configuration, machine_suffixes,
                                  master_accelerator, worker_accelerator,
                                  driver_provider):
    mig_startup_scripts = ["mig.sh"]
    self.createCluster(
        configuration,
        self.INIT_ACTIONS,
        machine_type="n1-standard-2",
        master_accelerator=master_accelerator,
        worker_accelerator=worker_accelerator,
        metadata=None,
        timeout_in_minutes=30,
        startup_scripts=mig_startup_scripts)
    for machine_suffix in machine_suffixes:
      self.verify_instance("{}-{}".format(self.getClusterName(),
                                          machine_suffix))

if __name__ == "__main__":
  absltest.main()
