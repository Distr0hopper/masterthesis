import { ApiProperty } from '@nestjs/swagger';
import { ParameterDirection } from '../enums';

export class ParameterDto {
    @ApiProperty()
    id: string;

    @ApiProperty({ example: 'maxspeed' })
    name: string;

    @ApiProperty({ example: 'double' })
    cwlType: string;

    @ApiProperty({ nullable: true, example: '20.0' })
    defaultValue: string | null;

    @ApiProperty({ nullable: true })
    description: string | null;

    @ApiProperty({ enum: ParameterDirection })
    direction: ParameterDirection;
}