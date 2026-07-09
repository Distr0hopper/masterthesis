import { ApiProperty } from '@nestjs/swagger';
import { IsIn, IsString } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

export class CreateComponentDto {
  @ApiProperty({ example: 'My EO Component' })
  @IsString()
  name: string;

  @ApiProperty({ enum: VALID_DOMAINS })
  @IsIn(VALID_DOMAINS)
  domain: string;
}