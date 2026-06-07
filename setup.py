from setuptools import setup, find_packages

setup(
    name='stm32_nucleo_pinout',
    version='0.9',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pandas',
        'Pillow>=11.0.0',
    ],
    entry_points={
        'console_scripts': [
            'stm32_nucleo_pinout=stm32_nucleo_pinout.stm32_nucleo_pinout:main',
        ],
    },
    author='Daniel Alvarez',
    author_email='danidask@gmail.com',
    description='A package to generate pinout images for STM32 Nucleo boards, based on STM32CubeIDE/STM32CubeMX report file',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/yourproject',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)