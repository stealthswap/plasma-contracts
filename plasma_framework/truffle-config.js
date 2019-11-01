require('dotenv').config(); // auto parse env variables from '.env' file

const HDWalletProvider = require('@truffle/hdwallet-provider');

const infuraUrl = `${process.env.INFURA_URL || 'https://infura.io/v3/'}/${process.env.INFURA_API_KEY}`;
const cleanInfuraUrl = infuraUrl.replace(/([^:])(\/\/+)/g, '$1/');

module.exports = {
    networks: {
        local: {
            host: process.env.ETH_CLIENT_HOST || '127.0.0.1',
            port: process.env.ETH_CLIENT_PORT || 8545,
            from: process.env.DEPLOYER_ADDRESS,
            gas: 6000000,
            network_id: '*',
        },
        mainnet: {
            host: process.env.ETH_CLIENT_HOST || '127.0.0.1',
            port: process.env.ETH_CLIENT_PORT || 8545,
            from: process.env.DEPLOYER_ADDRESS,
            network_id: 1,
        },
        rinkeby: {
            host: process.env.ETH_CLIENT_HOST || '127.0.0.1',
            port: process.env.ETH_CLIENT_PORT || 8545,
            from: process.env.DEPLOYER_ADDRESS,
            network_id: 4,
        },
        goerli: {
            host: process.env.ETH_CLIENT_HOST || '127.0.0.1',
            port: process.env.ETH_CLIENT_PORT || 8545,
            from: process.env.DEPLOYER_ADDRESS,
            network_id: 5,
        },
        infura: {
            skipDryRun: true,
            // Can't be a function otherwise it'll throw a JSON RPC error for some reason
            // https://github.com/trufflesuite/truffle/issues/852#issuecomment-522367001
            // Using 0's as private key because it'll throw an error if the private keys
            // are undefined as this is instanciating a class....
            provider: new HDWalletProvider(
                [
                    process.env.DEPLOYER_PRIVATEKEY || '0'.repeat(64),
                    process.env.MAINTAINER_PRIVATEKEY || '0'.repeat(64),
                    process.env.AUTHORITY_PRIVATEKEY || '0'.repeat(64),
                ],
                cleanInfuraUrl,
                0, 3,
            ),
            network_id: '*',
        },
    },

    // Set default mocha options here, use special reporters etc.
    mocha: {
        reporter: process.env.MOCHA_REPORTER || '',
        reporterOptions: {
            currency: 'USD',
            showTimeSpent: true,
            src: 'contracts/src/',
        },
    },

    // Configure your compilers
    compilers: {
        solc: {
            version: '0.5.11',
            settings: {
                optimizer: {
                    enabled: true,
                    runs: 200,
                },
            },
        },
    },

    plugins: ['solidity-coverage'],
};
