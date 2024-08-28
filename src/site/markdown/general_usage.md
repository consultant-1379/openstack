# General Usage
After the Deployer is made available on your system, it will be available to run from anywhere on the system.


## Checking The Version
You can check the version of the Deployer you currently have installed by running the following command.

```bash
deployer --version
```


## Getting Help
You can get help on the scripts usage from by running the following command.

```bash
deployer --help
```

The help output will show details on items such as how to set verbosity and use the scripts logging functionality.

The help output will also list all of the available commands within the Deployer along with a short description of each.

The Deployer commands aim to follow a convention of 'object' followed by an 'action'. The object could be a single word object like 'ci' indicting an action will be performed on a CI deployment. It could also be a multi word object like 'ci enm stacks' to indicate a set of stacks belonging to a enm ci deployment. For example to delete the stacks associated with a enm ci deployment, the command would be as follows.

```bash
deployer ci enm stacks delete
```

Each of these commands has its own set of help documentation and command line arguments. The help for any particular command can obtained by running.

```bash
deployer <object> <action> --help
```

For example to get help about how to use the stacks delete command, you could run this command.

```bash
deployer ci enm stacks delete --help
```


## Output Verbosity
The Deployer allows increasing the verbosity of its output by adding -v arguments. More -v arguments will further increase verbosity. Adding the -q argument will have the opposite effect, in lowering the verbosity.

Example of increasing verbosity by one level

```bash
deployer -v
```

Example of increasing verbosity by two levels

```bash
deployer -vv
```

Example of lowering verbosity

```bash
deployer -q
```


## Debug Mode
The Deployer by default when it hits an exception, may not report a full stack trace of that exception. To make sure the script always gives a full stack trace of any exceptions it runs into, it is recommended to always use debug mode.

Example below of using debug Mode

```bash
deployer --debug
```


## Logging
The Deployer has the ability to log its output to a log file. Below is an example of making the script log to a output.log file.

```bash
deployer --log-file output.log
```

